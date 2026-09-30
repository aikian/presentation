import io
import json
import logging
import re
import pandas as pd

from typing import Any, Dict, Optional
from urllib import error as urlerror
from urllib import request as urlrequest
from fastapi import UploadFile

from app.services.video_analyzer import _gemini_model_candidates, _generate_gemini_content

logger = logging.getLogger(__name__)

# 가중치 학습에 사용할 수 있는 최소 설문 응답자 수
MIN_RESPONSES = 20
    
# 설문 점수 범위
MIN_SURVEY_SCORE = 1
MAX_SURVEY_SCORE = 5

# 집중도 점수 범위
MIN_ATTENTION_SCORE = 0
MAX_ATTENTION_SCORE = 100

TOP_FEEDBACK_COUNT = 3

# 필수 컬럼
SURVEY_COLUMNS = [
    "participant_id",
    "spm",
    "pitch_variation",
    "db",
    "silence",
    "attention_score",
    "feedback"
] 
   
# 숫자로 변환할 컬럼
NUMERIC_COLUMNS = [
    "participant_id",
    "spm",
    "pitch_variation",
    "db",
    "silence",
    "attention_score"
] 

# 1~5점 범위의 설문 컬럼
FEATURE_COLUMNS = [
    "spm",
    "pitch_variation",
    "db",
    "silence"
]

# 규칙 기반 분류용 키워드, Gemini 요약이 실패했을 때만 사용
FEEDBACK_KEYWORDS = {
    "말하는 속도": ["속도", "빠르", "빨라", "느리", "느긋"],
    "정적/멈춤": ["정적", "끊기", "멈춤", "침묵", "끊겨"],
    "군말/추임새": ["추임새", "군말", "음..", "어.."],
    "어조/억양": ["단조", "억양", "어조", "강조"],
    "전달력/발음": ["목소리", "발음", "또렷", "전달력"],
    "내용 이해도": ["내용", "이해"]
}

def decode_csv(content: bytes) -> str:
    for encoding in ("utf-8-sig", "cp949"):
        try:
            return content.decode(encoding)
        except UnicodeDecodeError:
            continue
 
    raise ValueError("CSV 파일 인코딩을 읽을 수 없습니다. UTF-8 또는 CP949로 저장해 주세요.")

def mean_or_none(series: pd.Series, digits: int = 4) -> Optional[float]:
    values = series.dropna()
 
    if values.empty:
        return None
 
    return round(float(values.mean()), digits)

def _build_feedback_prompt(feedbacks: list[str], top_n: int) -> str:
    numbered = "\n".join(f"{i + 1}. {text}" for i, text in enumerate(feedbacks))
    return (
        "다음은 발표에 대한 청중 피드백 목록입니다. "
        f"의미가 비슷한 의견끼리 묶고, 가장 많이 언급된 순서로 상위 {top_n}개를 골라주세요.\n\n"
        f"{numbered}\n\n"
        "다른 설명 없이 아래 JSON 배열 형식으로만 응답하세요. 코드블록을 쓰지 마세요.\n"
        '[{"summary": "묶인 의견을 한 문장으로 요약", "count": 해당하는 응답 개수}]'
    )
    
# Gemini 실행에 실패했을 때 실행하는 규칙 기반 등장횟수 상위 N개 반환
def _fallback_top_feedbacks(feedbacks: list[str], top_n: int) -> list[dict[str, Any]]:
    category_counts: dict[str, int] = {category: 0 for category in FEEDBACK_KEYWORDS}
    
    for feedback in feedbacks:
        for category, keywords in FEEDBACK_KEYWORDS.items():
            if any(keyword in feedback for keyword in keywords):
                category_counts[category] += 1

    ranked = sorted(
        ((category, count) for category, count in category_counts.items() if count > 0),
        key=lambda item: item[1],
        reverse=True,
    )
    
    return [
        {"summary": f"'{category}' 관련 의견", "count": count}
        for category, count in ranked[:top_n]
    ]
    
# 비슷한 피드백끼리 묶어서 가장 많이 엄급된 상위 N개를 AI로 요약
def summarize_top_feedbacks(feedbacks: list[str], api_key: str, top_n: int = TOP_FEEDBACK_COUNT) -> list[dict[str, Any]]:
    if not feedbacks:
        return []
    
    if api_key:
        prompt = _build_feedback_prompt(feedbacks, top_n)
    
        for model_name in _gemini_model_candidates():
            try: 
                raw = _generate_gemini_content(model_name, api_key, prompt)
                if not raw:
                    continue
            
                cleaned = re.sub(r"^```(?:json)?|```$", "", raw, flags=re.MULTILINE).strip()
                parsed = json.loads(cleaned)
            
                if not isinstance(parsed, list):
                    raise ValueError("응답이 리스트 형식이 아닙니다.")
            
                return parsed[:top_n]
        
            except (urlerror.HTTPError, urlerror.URLError, TimeoutError, json.JSONDecodeError, ValueError) as exc:
                logger.warning("Gemini REST 피드백 요약 실패 (%s): %s", model_name, exc)
                
        logger.warning("모든 Gemini 모델에서 피드백 요약 실패, 규칙 기반으로 대체합니다.")
        
    return _fallback_top_feedbacks(feedbacks, top_n)

async def analyze_survey_csv(file: UploadFile, result_id: str, api_key: str) -> Dict[str, Any]:
    content = await file.read()
    
    if not content:
        raise ValueError("업로드된 파일이 비어 있습니다.")
    
    text = decode_csv(content)
    try:
        df = pd.read_csv(io.StringIO(text), header=None, na_values=["Null", "NULL", "none", ""])
    except Exception as e: 
        raise ValueError(f"CSV 파일을 읽는 중 오류가 발생했습니다: {e}")

    if df.empty:
        raise ValueError("CSV 파일이 비어 있습니다.")   
    
    if len(df.columns) != len(SURVEY_COLUMNS):
        raise ValueError(
            f"CSV 컬럼 수가 올바르지 않습니다. "
            f"필요한 컬럼 수: {len(SURVEY_COLUMNS)}, "
            f"현재 컬럼 수: {len(df.columns)}"
        )
        
    # 숫자여야 하는 컬럼의 SURVEY_COLUMNS 내 위치
    required_positions = [
        SURVEY_COLUMNS.index("participant_id"),
        SURVEY_COLUMNS.index("attention_score")
    ]
    first_row_numeric = pd.to_numeric(df.iloc[0, required_positions], errors="coerce")
    if first_row_numeric.isna().any():
        df = df.drop(0).reset_index(drop=True)

    df.columns = SURVEY_COLUMNS

    for column in NUMERIC_COLUMNS:
        df[column] = pd.to_numeric(df[column], errors="coerce")
    
    # 필수 데이터가 없는 응답제거
    df = df.dropna(subset=["participant_id", "attention_score"]).copy()
    
    if df.empty:
        raise ValueError("CSV 파일에 유효한 데이터가 없습니다.")

    if((df["attention_score"] < MIN_ATTENTION_SCORE).any() or (df["attention_score"] > MAX_ATTENTION_SCORE).any()):
        raise ValueError(f"설문 집중도 점수는 {MIN_ATTENTION_SCORE}에서 {MAX_ATTENTION_SCORE} 사이의 값이어야 합니다.")
    
    for column in FEATURE_COLUMNS:
        invalid_mask = (
            df[column].notna()
            & (
                (df[column] < MIN_SURVEY_SCORE)
                | (df[column] > MAX_SURVEY_SCORE)
            )
        )

        if invalid_mask.any():
            invalid_values = (
                df.loc[invalid_mask, column]
                .dropna()
                .unique()
                .tolist()
            )

            raise ValueError(
                f"{column}의 값은 "
                f"{MIN_SURVEY_SCORE}~{MAX_SURVEY_SCORE} "
                f"범위여야 합니다. "
                f"잘못된 값: {invalid_values}"
            )
            
    average_score = float(df["attention_score"].mean())

    feature_means: Dict[str, Any] = {
        column: mean_or_none(df[column]) for column in FEATURE_COLUMNS
    }
             
    feedbacks = []
    
    for feedback in df["feedback"]:
        if pd.isna(feedback):
            continue
        
        feedback = str(feedback).strip()
        
        if not feedback:
            continue
        
        feedbacks.append(feedback)
        
    top_feedbacks = summarize_top_feedbacks(feedbacks, api_key)
    
    result = {
        "result_id": result_id,
        "participant_count": len(df),
        "average_attention_score": round(float(average_score), 2),
        "feature_means": feature_means,
        "feedbacks": feedbacks,
        "top_feedbacks": top_feedbacks,
        # 응답자가 최소 인원 이상일 때만 가중치 업데이트에 사용
        "learning_data_available": len(df) >= MIN_RESPONSES
    }
    
    return result 
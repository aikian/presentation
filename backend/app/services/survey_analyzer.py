import io
from typing import Any, Dict, Optional

import pandas as pd
from fastapi import UploadFile

# DB에 저장되기 위한 설문 최소 응답자 수
MIN_RESPONSES = 20
    
# 설문 점수 범위
MIN_SURVEY_SCORE = 1
MAX_SURVEY_SCORE = 5

# 집중도 점수 범위
MIN_ATTENTION_SCORE = 0
MAX_ATTENTION_SCORE = 100

# 필수 컬럼
SURVEY_COLUMNS = [
    "participant_id",
    "audience_group",
    "spm",
    "pitch_variation",
    "db",
    "silence",
    "filler",
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
    "filler",
    "attention_score"
] 

# 1~5점 범위의 설문 컬럼
FEATURE_COLUMNS = [
    "spm",
    "pitch_variation",
    "db",
    "silence",
    "filler",
]

# 청중 그룹
VALID_GROUPS = {"major", "non_major"}

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

async def analyze_survey_csv(file: UploadFile, result_id: str) -> Dict[str, Any]:
    content = await file.read()
    
    if not content:
        raise ValueError("업로드된 파일이 비어 있습니다.")
    
    try:
        df = pd.read_csv(io.BytesIO(content), header=None, encoding='utf-8', na_values=["Null", "NULL", "none", ""])
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
    df = df.dropna(subset=["participant_id", "audience_group", "attention_score"]).copy()
    
    if df.empty:
        raise ValueError("CSV 파일에 유효한 데이터가 없습니다.")
    
    df["audience_group"] = df["audience_group"].astype(str).str.strip().str.lower()
    
    if((df["attention_score"] < MIN_ATTENTION_SCORE).any() or (df["attention_score"] > MAX_ATTENTION_SCORE).any()):
        raise ValueError(f"설문 집중도 점수는 {MIN_ATTENTION_SCORE}에서 {MAX_ATTENTION_SCORE} 사이의 값이어야 합니다.")
    
    # 청중 그룹 검사
    invalid_groups = set(df["audience_group"].dropna()) - VALID_GROUPS
    
    if invalid_groups:
        raise ValueError(
            f"잘못된 audience_group 값입니다: {invalid_groups}"
        )
    
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
    df["filler_reversed"] = MAX_SURVEY_SCORE + MIN_SURVEY_SCORE - df["filler"]
    
    feature_means: Dict[str, Any] = {}
    
    for column in FEATURE_COLUMNS:
        
        feature_means.append({
            column: mean_or_none(df[column])
        })
            
    feature_means["filler_reversed"] = mean_or_none(df["filler_reversed"])
        
    # 청중 그룹별 평균
    group_means = {}
    
    for group in VALID_GROUPS:
        group_df = df[df["audience_group"] == group]
        
        if group_df.empty:
            continue
        
        response_count = len(group_df)
        
        group_data = {
            "result_id": result_id,
            "audience_group": group,
            "response_count": response_count,
            
            "spm_mean": mean_or_none(group_df["spm"]),
           
            "pitch_variation_mean": mean_or_none(group_df["pitch_variation"]),
            
            "db_mean": mean_or_none(group_df["db"]),
           
            "silence_mean": mean_or_none(group_df["silence"]),
           
            "filler_reversed_mean": mean_or_none(group_df["filler_reversed"]),
           
            "attention_mean": round(float(group_df["attention_score"].mean()), 4),
           
            # 그룹별 설문 응답자가 최소 인원 이상일 때만 가중치 업데이트에 사용 가능
            "learning_data_available": response_count >= MIN_RESPONSES
        }
        
        group_means[group] = group_data
        
    feedbacks = []
    
    for feedback in df["feedback"]:
        if pd.isna(feedback):
            continue
        
        feedback = str(feedback).strip()
        
        if not feedback:
            continue
        
        feedbacks.append(feedback)

    # result 값을 DB에 저장하도록 수정 필요
    result = {
        "result_id": result_id,
        "participant_count": len(df),
        "average_attention_score": round(float(average_score), 2),
        "feature_means": feature_means,
        "group_means": group_means,
        "feedbacks": feedbacks
    }
    
    return result
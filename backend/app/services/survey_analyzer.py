import io
from typing import Any, Dict

import pandas as pd
from fastapi import UploadFile

# DB에 저장되기 위한 설문 최소 응답자 수
MIN_RESPONSES = 20
    
async def analyze_survey_csv(file: UploadFile, result_id: int) -> Dict[str, Any]:
    content = await file.read()
    
    if not content:
        raise ValueError("업로드된 파일이 비어 있습니다.")
    
    try:
        df = pd.read_csv(io.BytesIO(content), encoding='utf-8', na_values=["Null", "NULL", "none", ""])
    except Exception as e: 
        raise ValueError(f"CSV 파일을 읽는 중 오류가 발생했습니다: {e}")

    if df.empty:
        raise ValueError("CSV 파일이 비어 있습니다.")
    
    required_columns = [
        'participant_id', 
        'db', 
        'pitch', 
        'spm',
        'filler',
        'monotony',
        "survey_attention_score",
        "feedback"
    ]
    
    missing_columns = [col for col in required_columns if col not in df.columns]
    
    if missing_columns:
        raise ValueError(f"CSV 파일에 필요한 컬럼이 없습니다: {', '.join(missing_columns)}")
    
    numeric_columns = [
        "participant_id",
        "db",
        "pitch",
        "spm",
        "silence",
        "filler",
        "monotony",
        "survey_attention_score",
    ]

    for column in numeric_columns:
        df[column] = pd.to_numeric(
            df[column],
            errors="coerce"
        )
    
    df = df.dropna(subset=["survey_attention_score"])
    
    if df.empty:
        raise ValueError("CSV 파일에 유효한 데이터가 없습니다.")
    
    if((df["survey_attention_score"] < 0).any() or (df["survey_attention_score"] > 100).any()):
        raise ValueError("설문 집중도 점수는 0에서 100 사이의 값이어야 합니다.")
    
    average_score = float(df["survey_attention_score"].mean())
    
    # 발표 특징 별 평균 계산
    feature_columns = [
        "db",
        "pitch",
        "spm",
        "silence",
        "filler",
        "monotony"
    ]
    
    feature_means: Dict[str, Any] = {}
    
    for column in feature_columns:
        valid_values = df[column].dropna()
        
        if valid_values.empty:
            feature_means[column] = None
        else:
            feature_means[column] = round(float(valid_values.mean()), 4)
            
    participants = []
    
    for _, row in df.iterrows():
        participants.append({
            "participant_id": int(row["participant_id"]),
            "db": row["db"],
            "pitch": row["pitch"],
            "spm": row["spm"],
            "filler": row["filler"],
            "monotony": row["monotony"],
            "survey_attention_score": round(float(row["survey_attention_score"]),2),
            "feedback": row["feedback"]
        })
        
    mean_data = None
    if len(df) >= MIN_RESPONSES:

        mean_data = {
            "result_id": result_id,
            "response_count": len(df),
            "spm_mean": feature_means["spm"],
            "pitch_mean": feature_means["pitch"],
            "db_mean": feature_means["db_mean"],
            "silence_mean": feature_means["silence_mean"],
            "filler_mean": feature_means["filler_mean"],
            "monotony_mean": feature_means["monotony_mean"],
            "attention_mean": round(average_score,4,),
        }

    # result 값을 DB에 저장하도록 수정 필요
    result = {
        "result_id": result_id,
        "participant_count": len(df),
        "average_attention_score": round(float(average_score), 2),
        "participants": participants,
        "feature_means": feature_means,
        "feedbacks": [
            {
                "id": participant["participant_id"],
                "text": participant["feedback"],
            }
            for participant in participants
            if participant["feedback"]
        ],
        "mean_data_available": (len(df) >= MIN_RESPONSES),
        "mean_data": mean_data
    }
    
    return result
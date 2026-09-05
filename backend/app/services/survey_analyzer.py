import io
import pandas as pd
from fastapi import UploadFile

async def analyze_survey_csv(file: UploadFile, result_id: int):
    content = await file.read()
    
    if not content:
        raise ValueError("업로드된 파일이 비어 있습니다.")
    
    try:
        df = pd.read_csv(io.BytesIO(content), encoding='utf-8', na_values=["Null", "NULL", "none", ""])
    except Exception as e: 
        raise ValueError(f"CSV 파일을 읽는 중 오류가 발생했습니다: {e}")
    
    print("CSV 데이터:")
    print(df)
    
    if df.empty:
        raise ValueError("CSV 파일이 비어 있습니다.")
    
    print("컬럼:", df.columns.tolist())
    
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
    
    average_score = df["survey_attention_score"].mean()
    
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
        
    result = {
        "result_id": result_id,
        "participant_count": len(df),
        "average_attention_score": round(float(average_score), 2),
        "participants": participants,
        "feedbacks": [
            {
                "id": participant["participant_id"],
                "text": participant["feedback"],
            }
            for participant in participants
            if participant["feedback"]
        ]
    }
    
    print("분석 결과:")
    print(result)
    
    return result
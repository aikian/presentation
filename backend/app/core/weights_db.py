from typing import Any
from datetime import datetime, timezone

import pandas as pd

from app.core.database import get_supabase
from app.services.update_weight import DEFAULT_WEIGHT, update_model

WEIGHTS_ROW_ID = 1

def get_weights() -> dict[str, Any]:
    res = (
        get_supabase()
        .table("attention_weights")
        .select("*")
        .eq("id", WEIGHTS_ROW_ID)
        .limit(1)
        .execute()
    )
    if res.data:
        return res.data[0]

    payload = {
        "id": WEIGHTS_ROW_ID,
        "weights": DEFAULT_WEIGHT.copy(),
        "last_trained_presentation_count": 0
    }
    res = get_supabase().table("attention_weights").insert(payload).execute()
    return res.data[0] if res.data else payload


def update_weights(weights: dict[str, float], presentation_count: int) -> None:
    get_supabase().table("attention_weights").update(
        {
            "weights": weights, 
            "last_trained_presentation_count": presentation_count,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }
    ).eq("id", WEIGHTS_ROW_ID).execute()

def fetch_presentation_data() -> pd.DataFrame:
    res = (
        get_supabase()
        .table("survey_results")
        .select(
            "feature_means,average_attention_score,created_at"
        )
        .eq("learning_data_available", True)
        .order("created_at", desc=False)
        .execute()
    )
    
    rows = []
    for row in res.data or []:
        means = row.get("feature_means") or {}
        rows.append({
            "spm_mean": means.get("spm"),
            "pitch_variation_mean": means.get("pitch_variation"),
            "db_mean": means.get("db"),
            "silence_mean": means.get("silence"),
            "attention_mean": row["average_attention_score"],
            "created_at": row["created_at"],
        })
        
    return pd.DataFrame(rows)

def maybe_update_model() -> dict[str, Any] | None:
    current = get_weights()
    presentation_data = fetch_presentation_data()
    
    if presentation_data.empty:
        return None
    
    result = update_model(
        presentation_data,
        current["weights"],
        last_trained_count=current.get("last_trained_presentation_count", 0)
    )

    if result["updated"]:
        update_weights(
            result["updated_weights"],
            result["trained_presentation_count"]  # 전체 개수가 아니라 실제로 학습한 개수
        )

    return result
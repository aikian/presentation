from typing import Any
import pandas as pd

from app.core.database import get_supabase
from app.services.update_weight import update_group_model

_DEFAULT_GROUP_WEIGHTS = {
    "spm_penalty_weight": 0.5,
    "pitch_weight": 0.5,
    "db_boost_weight": 0.5,
    "silence_penalty_weight": 0.5,
    "filler_penalty_weight": 0.5,
}


def get_weights() -> dict[str, Any]:
    res = (
        get_supabase()
        .table("group_weights")
        .select("*")
        .limit(1)
        .execute()
    )
    if res.data:
        return res.data[0]

    payload = {
        "weights": _DEFAULT_GROUP_WEIGHTS,
        "last_trained_presentation_count": 0
    }
    res = get_supabase().table("group_weights").insert(payload).execute()
    return res.data[0] if res.data else payload


def update_weights(weights: dict[str, float], presentation_count: int) -> None:
    get_supabase().table("group_weights").update(
        {"weights": weights, "last_trained_presentation_count": presentation_count}
    ).execute()

def fetch_presentation_data() -> pd.DataFrame:
    res = (
        get_supabase()
        .table("survey_group_means")
        .select(
            "audience_group,spm_mean,pitch_variation_mean,db_mean,"
            "silence_mean,filler_reversed_mean,attention_mean,learning_data_available,created_at"
        )
        .eq("learning_data_available", True)
        .order("created_at", desc=False)
        .execute()
    )
    return pd.DataFrame(res.data)

def maybe_update_model() -> dict[str, Any] | None:
    current = get_weights()
    presentation_data = fetch_presentation_data()
    
    if presentation_data.empty:
        return None
    
    result = update_group_model(
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
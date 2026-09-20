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


def get_group_weights(audience_group: str) -> dict[str, Any]:
    res = (
        get_supabase()
        .table("group_weights")
        .select("*")
        .eq("audience_group", audience_group)
        .limit(1)
        .execute()
    )
    if res.data:
        return res.data[0]

    payload = {
        "audience_group": audience_group,
        "weights": _DEFAULT_GROUP_WEIGHTS,
        "last_trained_presentation_count": 0,
    }
    res = get_supabase().table("group_weights").insert(payload).execute()
    return res.data[0] if res.data else payload


def update_group_weights(audience_group: str, weights: dict[str, float], presentation_count: int) -> None:
    get_supabase().table("group_weights").update(
        {"weights": weights, "last_trained_presentation_count": presentation_count}
    ).eq("audience_group", audience_group).execute()

def fetch_group_presentation_data(audience_group: str, limit: int = 200) -> pd.DataFrame:
    res = (
        get_supabase()
        .table("survey_group_means")
        .select(
            "audience_group,spm_mean,pitch_variation_mean,db_mean,"
            "silence_mean,filler_reversed_mean,attention_mean,learning_data_available,created_at"
        )
        .eq("audience_group", audience_group)
        .eq("learning_data_available", True)
        .order("created_at", desc=False)
        .execute()
    )
    return pd.DataFrame(res.data)


def maybe_update_group_model(audience_group: str) -> dict[str, Any] | None:
    current = get_group_weights(audience_group)
    presentation_data = fetch_group_presentation_data(audience_group)
    
    if presentation_data.empty:
        return None
    
    result = update_group_model(
        presentation_data,
        audience_group,
        current["weights"],
        last_trained_count=current.get("last_trained_presentation_count", 0),
    )

    if result["updated"]:
        update_group_weights(
            audience_group,
            result["updated_weights"],
            result["trained_presentation_count"],  # 전체 개수가 아니라 실제로 학습한 개수
        )

    return result
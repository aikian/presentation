from typing import Any

from app.core.database import get_supabase

def insert_survey_result(result_id: str, survey: dict[str, Any]) -> dict[str, Any] | None:
    payload = {
        "result_id": result_id,
        "participant_count": survey["participant_count"],
        "average_attention_score": survey["average_attention_score"],
        "feature_means": survey.get("feature_means", {}),
        "feedbacks": survey.get("feedbacks", []),
        "learning_data_available": survey.get("learning_data_available", False)
    }
    res = get_supabase().table("survey_results").upsert(payload, on_conflict="result_id").execute()
    return res.data[0] if res.data else None
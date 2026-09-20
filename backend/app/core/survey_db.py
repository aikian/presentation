from typing import Any
from app.core.database import get_supabase

def insert_attention_prediction(session_id: str, prediction: dict[str, Any]) -> dict[str, Any] | None:
    payload = {
        "session_id": session_id,
        "status": prediction.get("status"),
        "error_code": prediction.get("error_code"),
        "message": prediction.get("message"),
        "attention_score": prediction.get("attention_score"),
        "timeline_second": prediction.get("timeline_second", []),
        "timeline_minute": prediction.get("timeline_minute", []),
        "total_stats": prediction.get("total_stats", {}),
    }
    res = get_supabase().table("attention_predictions").insert(payload).execute()
    return res.data[0] if res.data else None


def insert_survey_result(session_id: str, survey: dict[str, Any]) -> dict[str, Any] | None:
    payload = {
        "session_id": session_id,
        "participant_count": survey["participant_count"],
        "average_attention_score": survey["average_attention_score"],
        "feature_means": survey.get("feature_means", {}),
        "feedbacks": survey.get("feedbacks", []),
    }
    res = get_supabase().table("survey_results").insert(payload, on_conflict="session_id").execute()
    return res.data[0] if res.data else None


def insert_survey_group_means(
    survey_result_id: str, session_id: str, group_means: dict[str, dict]
) -> list[dict]:
    if not group_means:
        return []

    rows = [
        {
            "survey_result_id": survey_result_id,
            "session_id": session_id,
            "audience_group": group,
            "response_count": data["response_count"],
            "spm_mean": data.get("spm_mean"),
            "pitch_variation_mean": data.get("pitch_variation_mean"),
            "db_mean": data.get("db_mean"),
            "silence_mean": data.get("silence_mean"),
            "filler_reversed_mean": data.get("filler_reversed_mean"),
            "attention_mean": data["attention_mean"],
            "learning_data_available": data.get("learning_data_available", False),
        }
        for group, data in group_means.items()
    ]
    res = get_supabase().table("survey_group_means").upsert(rows, on_conflict="survey_result_id,audience_group").execute()
    return res.data or []
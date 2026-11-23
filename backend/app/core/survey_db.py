from typing import Any

from app.core.database import execute_supabase, get_supabase

def insert_survey_result(result_id: str, survey: dict[str, Any]) -> dict[str, Any] | None:
    payload = {
        "result_id": result_id,
        "participant_count": survey["participant_count"],
        "average_attention_score": survey["average_attention_score"],
        "feature_means": survey.get("feature_means", {}),
        "feedbacks": survey.get("feedbacks", []),
        "top_feedbacks": survey.get("top_feedbacks", []),
        "learning_data_available": survey.get("learning_data_available", False)
    }
    res = get_supabase().table("survey_results").upsert(payload, on_conflict="result_id").execute()
    return res.data[0] if res.data else None

# 설문 링크
def create_survey_link(token: str, user_id: str, expires_at_iso: str) -> dict[str, Any]:
    res = execute_supabase(
        lambda: get_supabase()
        .table("survey_links")
        .insert({"token": token, "user_id": user_id, "expires_at": expires_at_iso})
        .execute()
    )
    if not res.data:
        raise RuntimeError("설문 링크 생성에 실패했습니다.")
    return res.data[0]

def get_survey_link(token: str) -> dict[str, Any] | None:
    res = execute_supabase(
        lambda: get_supabase()
        .table("survey_links")
        .select("*")
        .eq("token", token)
        .limit(1)
        .execute()
    )
    return res.data[0] if res.data else None

def close_survey_link(token: str) -> None:
    execute_supabase(
        lambda: get_supabase()
        .table("survey_links")
        .update({"is_open": False})
        .eq("token", token)
        .execute()
    )
    
def attach_survey_to_result(token: str, result_id: str) -> None:
    execute_supabase(
        lambda: get_supabase()
        .table("survey_links")
        .update({"result_id": result_id})
        .eq("token", token)
        .execute()
    )  
      
    execute_supabase(
        lambda: get_supabase()
        .table("survey_responses")
        .update({"result_id": result_id})
        .eq("link_token", token)
        .execute()
    )
    
# 설문 응답
def save_survey_response(link: dict[str, Any], row: dict[str, Any]) -> None:
    # 같은 링크에 같은 participant_id가 있으면 update, 없으면 insert
    # 한 사람의 중복 답변 방지
    token = link["token"]
    payload = {"link_token": token, "result_id": link.get("result_id"), **row}
    
    exist = execute_supabase(
        lambda: get_supabase()
        .table("survey_responses")
        .select("id")
        .eq("link_token", token)
        .eq("participant_id", row["participant_id"])
        .limit(1)
        .execute()
    )
    if exist.data:
        execute_supabase(
            lambda: get_supabase()
            .table("survey_responses")
            .update(payload)
            .eq("id", exist.data[0]["id"])
            .execute()
        )
    
    else:
        execute_supabase(
            lambda: get_supabase()
            .table("survey_responses")
            .insert(payload)
            .execute()
        )
        
def fetch_survey_responses(result_id: str) -> list[dict[str, Any]]:
    res = execute_supabase(
        lambda: get_supabase()
        .table("survey_responses")
        .select("participant_id, spm, pitch_variation, db, silence, attention_score, feedback")
        .eq("result_id", result_id)
        .execute()
    )
    return res.data or []

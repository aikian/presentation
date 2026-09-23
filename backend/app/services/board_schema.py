"""발표 영상 공유 게시판 - 스냅샷/페이로드 빌더.

기능_추가_제안서.hwp "기능 1. 발표 영상 공유 게시판" 대응 모듈.
게시글을 등록할 때 analysis_results(+details, 스키마 v0.1)에서 검색/비교에 필요한
부분만 뽑아 board_posts.snapshot(jsonb)에 스냅샷으로 저장한다.

스냅샷을 따로 저장하는 이유:
- 원본 analysis_results가 나중에 삭제돼도 게시글의 요약 정보(점수 등)는 남아 있어야 한다.
- 목록/상세 API에서 매번 analysis_results를 join하지 않아도 되어 가볍다.

[이번 수정]
- snapshot에 metrics / audio_summary / coaching을 추가 (게시글 상세에서 "영상 + AI 분석 결과"를 함께 보여주기 위함)
- board_posts에 정렬·필터용 컬럼(score_total, is_public, author_name)을 함께 채운다.
"""
from typing import Any

SCHEMA_VERSION = "0.1"


def build_board_snapshot(analysis_result: dict[str, Any]) -> dict[str, Any]:
    """analysis_results 레코드 1건을 게시판용 JSON 조각(snapshot)으로 변환한다."""
    details = analysis_result.get("details") or {}
    audio_summary = (details.get("audio") or {}).get("summary")

    return {
        "schema_version": SCHEMA_VERSION,
        "board_snapshot": {
            "analysis_result_id": analysis_result.get("id"),
            # AHP 담당자가 details.scores를 구현하기 전까지는 평면 컬럼(score_*)으로 대체
            "scores": details.get("scores")
            or {
                "weights_version": None,
                "gaze": analysis_result.get("score_gaze"),
                "posture": analysis_result.get("score_pose"),
                "gesture": analysis_result.get("score_gesture"),
                "time": analysis_result.get("score_time"),
                "total": analysis_result.get("score_total"),
            },
            # 발표 간 비교(사용자 시나리오 5)에 쓰는 원시 지표
            "metrics": {
                "gaze_away_ratio": analysis_result.get("gaze_away_ratio"),
                "shoulder_tilt_avg": analysis_result.get("shoulder_tilt_avg"),
                "gesture_count": analysis_result.get("gesture_count"),
                "elapsed_sec": analysis_result.get("elapsed_sec"),
                "goal_sec": analysis_result.get("goal_sec"),
            },
            "audio_summary": audio_summary,           # 음성 분석 꺼짐/실패 시 null
            "summary": details.get("summary"),        # 영상 지표 담당자 구현 전엔 null
            "habits": details.get("habits"),          # 습관 탐지 담당자 구현 전엔 null
            "artifacts": details.get("artifacts") or {},
            "coaching": analysis_result.get("coaching"),
        },
    }


def _total_score(snapshot: dict[str, Any], analysis_result: dict[str, Any]) -> int:
    scores = snapshot["board_snapshot"].get("scores") or {}
    total = scores.get("total")
    if total is None:
        total = analysis_result.get("score_total")
    try:
        return int(total)
    except (TypeError, ValueError):
        return 0


def build_board_post(
    *,
    post_id: str,
    user_id: str,
    author_name: str | None,
    title: str,
    topic: str,
    tags: list[str],
    video_storage_path: str,
    is_public: bool,
    analysis_result: dict[str, Any],
) -> dict[str, Any]:
    """board_posts INSERT에 사용할 전체 payload를 만든다.

    video_storage_path: Supabase Storage 경로 (계획서 리스크 대응:
    "Supabase Storage를 이용하여 영상 파일 저장, DB에는 경로만").
    """
    snapshot = build_board_snapshot(analysis_result)
    return {
        "id": post_id,
        "user_id": user_id,
        "author_name": author_name,
        "analysis_result_id": analysis_result.get("id"),
        "title": title,
        "topic": topic,
        "tags": tags,
        "video_url": video_storage_path,
        "is_public": is_public,
        "score_total": _total_score(snapshot, analysis_result),
        "snapshot": snapshot,
    }

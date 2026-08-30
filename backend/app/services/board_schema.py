"""[신규 추가] 발표 영상 공유 게시판 기능.

기능_추가_제안서.hwp "기능 1. 발표 영상 공유 게시판" 대응 모듈.
게시글을 등록할 때 analysis_results.details(스키마 v0.1)에서 검색/비교에
필요한 부분만 뽑아 board_posts.snapshot(jsonb)에 스냅샷으로 저장한다.

스냅샷을 따로 저장하는 이유:
- 원본 analysis_results가 나중에 삭제/비공개 처리돼도 게시글 자체의
  요약 정보(점수, 태그 검색용 요약)는 게시판에 남아 있어야 한다.
- 목록/검색 API에서 매번 analysis_results를 join하지 않아도 되어 가볍다.
"""
from typing import Any

SCHEMA_VERSION = "0.1"


def build_board_snapshot(analysis_result: dict[str, Any]) -> dict[str, Any]:
    """analysis_results 레코드 1건을 게시판용 JSON 조각(snapshot)으로 변환한다.

    Args:
        analysis_result: supabase `analysis_results` 테이블의 행(dict).
                          details 컬럼(schema v0.1)이 있으면 함께 활용한다.

    Returns:
        스키마 v0.1을 따르는 board snapshot JSON 조각. 예)
        {
          "schema_version": "0.1",
          "board_snapshot": {
            "analysis_result_id": "...",
            "scores": { "weights_version": "ahp-v1", "total": 78, ... },
            "summary": { "gaze_away_ratio": 0.18, ... },   # 담당자 구현 전엔 null
            "habits": [...],                                # 담당자 구현 전엔 null
            "artifacts": { "gaze_heatmap_png": "storage://..." }
          }
        }
    """
    details = analysis_result.get("details") or {}

    return {
        "schema_version": SCHEMA_VERSION,
        "board_snapshot": {
            "analysis_result_id": analysis_result.get("id"),
            # AHP 담당자가 scores 블록을 구현하기 전까지는 평면 컬럼(score_*)으로 대체
            "scores": details.get("scores") or {
                "weights_version": None,
                "gaze": analysis_result.get("score_gaze"),
                "posture": analysis_result.get("score_pose"),
                "gesture": analysis_result.get("score_gesture"),
                "total": analysis_result.get("score_total"),
            },
            "summary": details.get("summary"),   # 영상 지표 담당자 구현 전엔 null
            "habits": details.get("habits"),     # 습관 탐지 담당자 구현 전엔 null
            "artifacts": details.get("artifacts") or {},
        },
    }


def build_board_post(
    *,
    post_id: str,
    user_id: str,
    title: str,
    topic: str,
    tags: list[str],
    video_storage_path: str,
    analysis_result: dict[str, Any],
) -> dict[str, Any]:
    """게시글 INSERT에 사용할 전체 payload를 만든다. snapshot은 위 함수로 생성.

    video_storage_path: Supabase Storage 경로 (계획서 리스크 대응: "Supabase
    Storage를 이용하여 영상 파일 저장, DB에는 경로만").
    """
    snapshot = build_board_snapshot(analysis_result)
    return {
        "id": post_id,
        "user_id": user_id,
        "analysis_result_id": analysis_result.get("id"),
        "title": title,
        "topic": topic,
        "tags": tags,
        "video_url": video_storage_path,
        "snapshot": snapshot,
    }

"""`speakers.json`을 Supabase의 `reference_speakers` 테이블에 적재한다.

롤모델 비교(`app.services.rolemodel`)는 기준선을 DB에서 읽는다.
분석 서버가 JSON 파일을 직접 읽지 않는 이유는, 연사를 추가했을 때
서버를 다시 배포하지 않고 이 스크립트만 돌리면 되게 하기 위해서다.

**여러 번 돌려도 안전하다.** 영상 ID를 기본키로 upsert하므로,
연사를 추가한 뒤 다시 돌리면 기존 행은 갱신되고 새 행만 늘어난다.

`video_summary`는 건드리지 않는다. 표정·시선 지표는 담당자가 따로 채울 자리라
여기서 null로 덮어쓰면 남의 작업을 지우게 된다.
"""
import json
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
SPEAKERS = Path(__file__).parent / "speakers.json"

# 이 스크립트는 backend 밖에 있어서 app 패키지가 경로에 없다.
# .env 읽기와 키 선택 규칙을 그대로 재사용하려고 backend를 경로에 넣는다.
sys.path.insert(0, str(BASE_DIR / "backend"))

from app.core.database import get_supabase  # noqa: E402

TABLE = "reference_speakers"


def to_row(video_id: str, entry: dict) -> dict:
    """speakers.json 한 항목을 테이블 한 행으로 바꾼다."""
    speaker = entry.get("speaker") or {}

    return {
        "id": video_id,
        "name": speaker.get("name"),
        "affiliation": speaker.get("affiliation"),
        # episode는 "세바시 1491회"처럼 채널명을 이미 포함한다.
        # channel만 넣으면 회차를 잃어버리므로 episode를 우선한다.
        "source": entry.get("episode") or entry.get("channel"),
        "source_url": entry.get("youtube_url"),
        "title": entry.get("title"),
        "duration_sec": entry.get("duration_sec"),
        "usable_sec": entry.get("usable_sec"),
        "audio_summary": entry.get("audio_summary"),
    }


def load(path: Path = SPEAKERS) -> list[dict]:
    """적재할 행을 만든다. 음성 지표가 없는 항목은 거른다.

    `audio_summary`가 없는 연사는 기준선 계산에 아무 기여도 못 하면서
    `reference_count`만 부풀린다. 비교 결과에 "발표 7편 기준"이라고
    적히는데 실제로는 5편만 쓴 상황이 되므로 아예 넣지 않는다.
    """
    data = json.loads(path.read_text(encoding="utf-8"))

    rows, skipped = [], []
    for video_id, entry in data.items():
        if not entry.get("audio_summary"):
            skipped.append(video_id)
            continue
        rows.append(to_row(video_id, entry))

    if skipped:
        print(f"건너뜀 (음성 지표 없음): {', '.join(skipped)}")

    return rows


if __name__ == "__main__":
    rows = load()
    if not rows:
        print("적재할 연사가 없습니다.")
        raise SystemExit(1)

    supabase = get_supabase()
    supabase.table(TABLE).upsert(rows).execute()

    saved = supabase.table(TABLE).select("id,name,source").execute().data or []
    print(f"적재 완료: {len(rows)}편 → 테이블 {len(saved)}편")
    for row in sorted(saved, key=lambda r: (r.get("name") or "", r.get("source") or "")):
        print(f"  {row.get('name')}  {row.get('source')}")

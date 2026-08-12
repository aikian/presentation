"""분석 결과를 팀 공유 스키마(docs/schema/) 형식의 JSON으로 변환한다.

analysis_results.details 컬럼에 이 JSON을 통째로 저장한다.
기존 평면 컬럼(gaze_away_ratio 등)은 호환용으로 그대로 유지한다.

스키마 v0.1 규약 중 이 파일이 지키는 것:
- 없는 값은 None(null). 0은 "측정된 0"이라는 뜻이라 절대 혼용하지 않는다.
- 시간은 영상 시작 = 0초 기준 float 초(소수 1자리), 리스트는 시간 오름차순.
- 블록마다 주인이 1명이다. 지금은 meta·audio만 채우고 나머지는 None으로 둔다.
  담당자가 자기 블록을 구현하면 이 파일에 채우는 함수를 추가한다.
"""
from typing import Any

SCHEMA_VERSION = "0.1"


def _audio_summary(audio: dict[str, Any], duration_sec: float | None) -> dict[str, Any]:
    silence_ratio = audio.get("audio_silence_ratio")
    silence_total = (
        round(silence_ratio * duration_sec, 1)
        if silence_ratio is not None and duration_sec
        else None
    )

    return {
        "spm_avg": audio.get("speech_rate_spm"),
        "filler_count": audio.get("filler_count"),
        "filler_per_min": audio.get("filler_per_min"),
        # 짧은 무음까지 포함한 전체 무음 시간. silences[]는 2초 이상만 담으므로
        # sum(silences) <= silence_total_sec 이다.
        "silence_total_sec": silence_total,
        "silence_ratio": silence_ratio,
        "pitch_std": audio.get("pitch_std_hz"),
        "monotone_ratio": audio.get("monotone_ratio"),
        # 실험 필드(x_): 회의에서 정식 승격하거나 삭제한다.
        "x_pitch_cv": audio.get("pitch_cv"),
        "x_pitch_median_hz": audio.get("pitch_median_hz"),
        "x_filler_detail": audio.get("filler_detail") or None,
    }


def build_audio_block(audio: dict[str, Any] | None, duration_sec: float | None) -> dict[str, Any] | None:
    """audio_analyzer.analyze_audio() 결과를 스키마의 audio 블록으로 변환한다.

    음성 분석이 꺼져 있거나 실패했으면 None을 반환한다.
    analyze_audio는 실패해도 예외 대신 0으로 채운 dict를 돌려주는데,
    그 0을 그대로 저장하면 "필러워드 0회"처럼 측정된 값으로 오해된다.
    """
    if not audio or not audio.get("speech_available"):
        return None

    return {
        "transcript": audio.get("segments") or [],
        "timeline": audio.get("timeline") or None,
        "filler_words": audio.get("filler_words") or [],
        # analyze_audio의 long_silences는 {start, sec} 형식이라 {start, end}로 바꾼다.
        "silences": [
            {"start": gap["start"], "end": round(gap["start"] + gap["sec"], 1)}
            for gap in audio.get("long_silences") or []
        ],
        "summary": _audio_summary(audio, duration_sec),
    }


def build_details(
    metrics: dict[str, Any],
    *,
    duration_sec: float | None = None,
    frame_interval_sec: float | None = None,
    target_time_sec: float | None = None,
) -> dict[str, Any]:
    """분석 결과 전체를 스키마 JSON으로 만든다.

    아직 주인이 구현하지 않은 블록은 None이다. 읽는 쪽은 null 방어가 필수다.
    """
    audio_metrics = metrics.get("audio_metrics")
    audio_duration = (audio_metrics or {}).get("duration_sec") or None

    return {
        "schema_version": SCHEMA_VERSION,
        "meta": {
            "duration_sec": duration_sec or audio_duration,
            "frame_interval_sec": frame_interval_sec,
            "target_time_sec": target_time_sec,
        },
        "video_timeline": None,   # 시선·표정 / 자세·제스처 담당
        "audio": build_audio_block(audio_metrics, duration_sec or audio_duration),
        "summary": None,          # 영상 지표 집계 담당
        "scores": None,           # AHP 담당 (지금은 평면 컬럼 score_* 사용)
        "habits": None,           # 습관 탐지 담당
        "artifacts": {},          # 생성 파일이 있는 사람이 각자 경로를 넣는다
        # 롤모델 비교. 스키마 v0.1에 없는 실험 필드라 x_ 접두사를 쓴다.
        # 회의에서 정식 필드로 승격할지 정한다.
        "x_rolemodel": metrics.get("rolemodel_comparison"),
    }

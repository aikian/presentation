// 감점/가점 이벤트 분류(그래프 마커 색상 결정용)
export const NEGATIVE_EVENTS = new Set(["fast_spm", "slow_spm", "silence", "monotone", "excessive_pitch"]);
export const POSITIVE_EVENTS = new Set(["reengagement", "db_boost"]);

// 이벤트 코드 -> 표시용 라벨/색상
export const EVENT_META = {
    fast_spm: { label: "빠른 말속도", tone: "negative" },
    slow_spm: { label: "느린 말속도", tone: "negative" },
    silence: { label: "긴 정적", tone: "negative" },
    monotone: { label: "단조로운 어조", tone: "negative" },
    excessive_pitch: { label: "과도한 어조 변화", tone: "negative" },
    reengagement: { label: "어조 환기", tone: "positive" },
    db_boost: { label: "음량 강조", tone: "positive" }
}
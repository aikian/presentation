from typing import Any, List, Optional, Tuple
import statistics
import logging
import numpy as np
import math

from collections import deque

from app.core.weights_db import get_weights
from app.services.speech_feature import merge_speech_result
from app.services.audio_features import PITCH_MIN_HZ

logger = logging.getLogger(__name__)

# 기본 가중치 설정 (청중 설문 피드백에 따라 동적으로 갱신 가능)
DEFAULT_WEIGHT: dict[str, Any] = {
    "base_score": 85.0,
    
    # 말속도 관련 가중치
    "spm_penalty_weight": 0.5,
    # 최근 20초 중 60% 이상이 빠르거나 느리면 감점
    "spm_window_sec": 20,
    "spm_ratio_threshold": 0.6,
    "spm_penalty_cooldown_sec": 20,
    "spm_silence_count_threshold": 2, 
    
    # 정적 관련 가중치
    "silence_penalty_weight": 0.5,
    "silence_penalty_max_multiplier": 3.0,
    
    # 단조로움 가중치
    "monotone_consecutive_count_limit": 10, # 10(+7)초 이상 단조로울 시 감점 
    # 단조로움 이후 환기
    "reengagement_count": 2, # 2(+7)초 이상 지속 시 가점
    # 과도한 어조 변화
    "excessive_count": 8, # 8(+7)초 이상 지속 시 감점
    # pitch 가중치
    "pitch_weight": 0.5,
    
    # 음량 강조
    "db_boost_weight": 0.5,
    "db_reengagement_window_sec": 15
}

# 테스트를 통해 수정 필요
DEFAULT_THRESHOLD: dict[str, Any] = {
    # 말속도
    "fast_spm_threshold": 380.0,
    "slow_spm_threshold": 200.0,
    
    # 정적(4초 이상 지속 시 감점)
    "silence_penalty_threshold": 4.0,
    
    # 최근 pitch의 반음(semitone) 변동 표준편차가 1.5 이하이면 단조로운 어조로 판단
    "monotone_penalty_threshold": 1.5,
    
    # 단조로움 이후 최근 pitch의 반음(semitone) 변동 표준편차가 2.2 이상이면 어조 환기로 판단
    "reengagement_pitch_threshold": 2.2,
    
    # 최근 pitch의 반음(semitone) 변동 표준편차가 5.5 이상이면 과도한 어조로 판단
    "excessive_pitch_threshold": 5.5,
    
    # 음량 강조
    "db_zscore_threshold": 1.3,
    
    "max_penalty_per_sec": 5.0
}

# 에러 발생 시 에러 결과 반환
def make_error_result(code: str, message: str) -> dict[str, Any]:
    return {
        "status": "ERROR",
        "error_code": code,
        "message": message,
        "attention_score": None,
        "base_score": None,
        "timeline_second": [],
        "timeline_minute": [],
        "total_stats": {}
    }

def build_silence_penalty_secs(
    silence_data: List[dict[str, float]], 
    min_duration: float, 
    penalty_weight: float, 
    max_multiplier: float
) -> dict[int, dict[str, float]]:
    
    penalty_secs: dict[int, dict[str, float]] = {}
 
    for silence in silence_data:
        duration = silence["duration"]
        if duration < min_duration:
            continue
        
        multiplier = min(duration / min_duration, max_multiplier)
        
        penalty_secs[int(silence["end"])] = {
            "duration": duration,
            "penalty": round(penalty_weight * multiplier, 3)
        }
 
    return penalty_secs

# pitch 변동 계산: 창 안의 pitch를 반음(semitone) 단위로 바꾼 뒤 표준편차를 구함
def calculate_pitch_v(pitches: List[float]) -> Optional[float]:
    
    valid_pitches = [pitch for pitch in pitches if pitch is not None and pitch >= PITCH_MIN_HZ + 3]
    
    if len(valid_pitches) < 5:
        return None
    
    filtered_pitches = valid_pitches
    
    # 이상치 제거 (값이 6개 이상일 때만)
    if len(valid_pitches) >= 6:
        low_cutoff, high_cutoff = np.percentile(valid_pitches, [10, 90])
        filtered_pitches = [p for p in valid_pitches if low_cutoff <= p <= high_cutoff]
    
    if len(filtered_pitches) < 5:
        return None
    
    # 중앙값 기준 반음 차이로 변환: 12 * log2(f / 기준)
    reference = statistics.median(filtered_pitches)
    if reference <= 0:
        return None
    
    semitones = [12 * math.log2(p / reference) for p in filtered_pitches]
    
    return statistics.stdev(semitones)

# 최근 SPM 평균
def get_average_spm(spm_data:dict[int, float], sec:int, window: int = 5) -> Optional[float]:
    start = max(0,sec - window + 1)
    end =  sec + 1
    
    spm_values = [spm_data[i] for i in range(start, end) if i in spm_data and spm_data[i] > 0]
    
    if len(spm_values) < 3:
        return None
    
    return statistics.mean(spm_values)

# 최근 pitch 변동
def get_pitch_variation(pitch_data: dict[int, float], sec: int, window: int = 8) -> Optional[float]:
    start = max(0, sec - window + 1)
    
    pitches = [pitch_data[i] for i in range(start, sec + 1) if i in pitch_data and pitch_data[i] > 0]
    
    return calculate_pitch_v(pitches)

# 분단위 결과 생성
def make_min_timeline(sec_scores: List[dict[str, Any]]) -> List[dict[str, Any]]:
    if not sec_scores:
        return []
    
    min_group: dict[int, List[dict[str, Any]]] = {}
    
    for item in sec_scores:
        sec = item["sec"]
        minute = sec // 60
        
        if minute not in min_group:
            min_group[minute] = []
            
        min_group[minute].append(item)
        
    min_scores = []
    for minute in sorted(min_group):
        items = min_group[minute]
        scores = [item["score"] for item in items]
        penalties = []
        boosts = []
        event_counts: dict[str, int] = {}  
        
        for item in items:
            penalties.extend(item.get("penalties", []))
            boosts.extend(item.get("boosts", []))
            
            for code in item.get("events", []):
                event_counts[code] = event_counts.get(code, 0) + 1
                
        min_scores.append({
            "minute": minute,
            "score": round(statistics.mean(scores), 1),
            "penalties": penalties,
            "boosts": boosts,
            "events": event_counts
        })

    return min_scores

# 집중도 예측 함수
def predict_attention(speech_result: Optional[dict[str, Any]], audience_weight: Optional[dict[str, Any]]) -> dict[str, Any]:
    weight = DEFAULT_WEIGHT.copy()
    threshold = DEFAULT_THRESHOLD.copy()
    
    if audience_weight:
        unknown_keys = set(audience_weight) - set(DEFAULT_WEIGHT)
        if unknown_keys:
            logger.warning("알 수 없는 가중치 키 무시: %s", sorted(unknown_keys))
        weight.update({k: v for k, v in audience_weight.items() if k in DEFAULT_WEIGHT})
    
    if not speech_result:
        return make_error_result("NO_SPEECH_RESULT", "음성 분석 데이터가 전달되지 않았습니다.")
    
    duration = float(speech_result.get("duration_sec", 0.0))
    if duration <= 0:
        return make_error_result("INVALID_DURATION", "발표 시간을 측정할 수 없습니다")
    
    seconds = speech_result.get("seconds")
    spm_data = speech_result.get("spm_data")
    silence_data = speech_result.get("silence_data") or []
    
    # 청중에게 부정적인 영향을 주는 긴 정적(정적의 길이: 4초 ~)
    silence_penalty_secs = build_silence_penalty_secs(silence_data, threshold["silence_penalty_threshold"], weight["silence_penalty_weight"], weight["silence_penalty_max_multiplier"])
    pitch_data = speech_result.get("pitch_data") or {}
    norm_db_data = speech_result.get("norm_db_data")
    
    if not seconds or not spm_data or not norm_db_data:
        return make_error_result("NO_DATA", "필수 데이터(seconds)가 존재하지 않습니다")
    
    if not pitch_data:
        logger.warning("pitch_data가 비어 있어 단조로움/과도한 어조 변화 평가를 건너뜁니다")
    
    # 초 단위 집중도 저장
    sec_scores: List[dict[str, Any]] = []
    
    # 상태 변수 초기화
    monotone_duration = 0
    reengagement_duration = 0
    excessive_duration = 0
    monotone_detected = False
    last_dip_sec = float("-inf") # 정적/단조로움 감점이 마지막으로 발생한 초
    
    # 말속도: 최근 구간 내 분류 이력 + 감점 쿨다운
    spm_history: deque = deque()  # (sec, "fast" | "slow" | "normal")
    last_spm_penalty_sec = {"fast": float("-inf"), "slow": float("-inf")}
    
    # 말속도 판정 범위 내에 호흡(pause)가 충분한지 보는 지표(정적의 길이: 1.5~)
    silence_ends = [int(s["end"]) for s in silence_data]
    monotone_history: deque = deque()
    
    total_stats = {
        "total_spm_penalty_counts": 0,
        "total_monotone_counts": 0,
        "total_excessive_pitch_counts": 0,
        "total_silence_counts": 0,
        "total_reengagement_boost_counts": 0,
        "total_db_boost_counts": 0
    }
    
    monotone_threshold = threshold["monotone_penalty_threshold"]
    reengagement_threshold = threshold["reengagement_pitch_threshold"]
    excessive_threshold = threshold["excessive_pitch_threshold"]
                
    monotone_limit = weight["monotone_consecutive_count_limit"]
    reengagement_limit = weight["reengagement_count"]
    excessive_limit = weight["excessive_count"]
    
    # 창이 충분히 차기 전(영상 초반 등)에는 말속도 판정을 하지 않음
    min_spm_samples = max(3, int(weight["spm_window_sec"] * 0.5))     # 창 20초면 10개
    min_pitch_samples = max(3, int(weight["spm_window_sec"] * 0.3))   # 창 20초면 6개
    
    base_score = weight["base_score"]
    running_score = base_score
    
    # 초 단위 평가
    for idx, raw_sec in enumerate(seconds):
        sec = int(raw_sec if raw_sec is not None else idx)
        sec_delta = 0.0
        penalties_applied = []
        boosts_applied = []
        events_applied: List[str] = [] 
        
        pitch_v = get_pitch_variation(pitch_data, sec)
        if pitch_v is not None:
            monotone_history.append((sec, pitch_v <= monotone_threshold))
            
        while monotone_history and monotone_history[0][0] < sec - weight["spm_window_sec"] + 1:
            monotone_history.popleft()
            
        # 말속도
        average_spm = get_average_spm(spm_data, sec)
        
        if average_spm is not None:
            if average_spm > threshold["fast_spm_threshold"]:
                classification = "fast"
            elif average_spm < threshold["slow_spm_threshold"]:
                classification = "slow"
            else:
                classification = "normal"
            
            spm_history.append((sec, classification))
            
            window_start = max(sec - weight["spm_window_sec"] + 1, 0)
            
            while spm_history and spm_history[0][0] < window_start:
                spm_history.popleft()
                
            valid_count = len(spm_history)
            if valid_count >= min_spm_samples:
                fast_ratio = sum(1 for _, state in spm_history if state == "fast") / valid_count
                slow_ratio = sum(1 for _, state in spm_history if state == "slow") / valid_count
                
                is_monotone_context = (
                    len(monotone_history) >= min_pitch_samples
                    and sum(1 for _, m in monotone_history if m) / len(monotone_history) >= weight["spm_ratio_threshold"]
                )
                recent_silence_count = sum(1 for e in silence_ends if sec - weight["spm_window_sec"] < e <= sec)
                has_silence = recent_silence_count >= weight["spm_silence_count_threshold"]
                
                if (
                    fast_ratio >= weight["spm_ratio_threshold"] 
                    and is_monotone_context
                    and not has_silence
                    and sec - last_spm_penalty_sec["fast"] >= weight["spm_penalty_cooldown_sec"]
                ):
                    spm_penalty = weight["spm_penalty_weight"]
                    sec_delta -= spm_penalty
                    penalties_applied.append(f"최근 {weight['spm_window_sec']}초 중 {fast_ratio:.0%} 빠른 말속도 (-{spm_penalty:.1f})")
                    total_stats["total_spm_penalty_counts"] += 1
                    events_applied.append("fast_spm")
                    last_spm_penalty_sec["fast"] = sec
                    
                elif (
                    slow_ratio >= weight["spm_ratio_threshold"]
                    and is_monotone_context
                    and has_silence
                    and sec - last_spm_penalty_sec["slow"] >= weight["spm_penalty_cooldown_sec"]
                ):
                    spm_penalty = weight["spm_penalty_weight"]
                    sec_delta -= spm_penalty
                    penalties_applied.append(f"최근 {weight['spm_window_sec']}초 중 {slow_ratio:.0%} 느린 말속도 (-{spm_penalty:.1f})")
                    total_stats["total_spm_penalty_counts"] += 1
                    events_applied.append("slow_spm")
                    last_spm_penalty_sec["slow"] = sec
        
        # 정적 평가
        if sec in silence_penalty_secs:
            silent = silence_penalty_secs[sec]
            sec_delta -= silent["penalty"]
            penalties_applied.append(f"{silent['duration']:.1f}초 정적 감지 (-{silent['penalty']:.1f})")
            events_applied.append("silence")
            total_stats["total_silence_counts"] += 1
            last_dip_sec = sec
            
        # 단조로움 평가
        if pitch_v is None:
            pass
        
        elif pitch_v <= monotone_threshold:
            monotone_duration += 1
            reengagement_duration = 0
            excessive_duration = 0
                
            if monotone_duration >= monotone_limit:
                penalty = weight["pitch_weight"]
                sec_delta -= penalty
                penalties_applied.append(f"{monotone_duration}초 연속 단조로운 어조 (-{penalty:.1f})")
                total_stats["total_monotone_counts"] += 1
                events_applied.append("monotone")
                last_dip_sec = sec
                
                monotone_detected = True
                monotone_duration = 0
                    
        elif reengagement_threshold <= pitch_v < excessive_threshold:
            excessive_duration = 0
            
            if monotone_detected:
                reengagement_duration += 1
                
                if reengagement_duration >= reengagement_limit:
                    boost = weight["pitch_weight"]
                    sec_delta += boost
                    boosts_applied.append(f"단조로움 이후 피치 변화 (+{boost:.1f})")
                    total_stats["total_reengagement_boost_counts"] += 1
                    events_applied.append("reengagement")
                    
                    monotone_detected = False
                    reengagement_duration = 0
                    
            else:
                reengagement_duration = 0
            
            monotone_duration = 0
                        
        elif excessive_threshold <= pitch_v:
            reengagement_duration = 0
            monotone_duration = 0
                
            excessive_duration += 1
            if excessive_duration >= excessive_limit:
                penalty = weight["pitch_weight"]
                sec_delta -= penalty
                penalties_applied.append(f"{excessive_duration}초 연속 과도한 어조 변화 (-{penalty:.1f})")
                total_stats["total_excessive_pitch_counts"] += 1
                events_applied.append("excessive_pitch")
                
                excessive_duration = 0
                
        else:
            monotone_duration = 0
            excessive_duration = 0
            reengagement_duration = 0
            
        # 단조로움 및 정적 이후 음량 강조 평가
        sustain = 2
        recent_db = [norm_db_data.get(i) for i in range(sec - sustain + 1, sec + 1)]
        
        # 박수나 소음이 음량 강조로 잡히는 것을 완화하기 위해 pitch와 spm으로 실제 발화일 떄만 가점
        recent_pitch_valid = all(
            get_pitch_variation(pitch_data, i) is not None
            for i in range(sec - sustain + 1, sec + 1)
        )
        recent_spm_valid = all(
            get_average_spm(spm_data, i) is not None
            for i in range(sec - sustain + 1, sec + 1)
        )
        
        if(
            recent_pitch_valid
            and recent_spm_valid
            and all(v is not None and v >= threshold["db_zscore_threshold"] for v in recent_db)
            and sec - sustain + 1 > last_dip_sec
            and sec - last_dip_sec <= weight["db_reengagement_window_sec"]
        ):
            boost = weight["db_boost_weight"]
            sec_delta += boost
            boosts_applied.append(f"정적/단조로움 이후 음량 강조 (+{boost:.1f})")
            total_stats["total_db_boost_counts"] += 1
            events_applied.append("db_boost")
            last_dip_sec = float("-inf")
            
        running_score += max(sec_delta, -threshold["max_penalty_per_sec"])
        running_score = max(0.0, min(100.0, running_score))
 
        sec_scores.append({
            "sec": sec,
            "score": round(running_score, 1),
            "penalties": penalties_applied,
            "boosts": boosts_applied,
            "events": events_applied
        })
        
    final_score = sec_scores[-1]["score"]
    
    # 분 단위 결과
    min_score = make_min_timeline(sec_scores)
    
    return {
        "status": "SUCCESS",
        "error_code": None,
        "message": "집중도 추정 성공",
        "attention_score": final_score,
        "base_score": base_score,
        "timeline_second": sec_scores,
        "timeline_minute": min_score,
        "total_stats": total_stats,
    }

def analyze_audience(audio_metrics: dict[str, Any], audio_features: dict[str, Any]) -> dict[str, Any]:
    # DB에서 가중치를 가져옴 만약에 없으면 DEFAULT_WEIGHT를 가중치로 사용
    audience_weight: Optional[dict[str, Any]] = None
    
    try:
        audience_weight = get_weights()["weights"]
    except Exception:
        logger.exception("가중치 조회 실패, 기본 가중치를 사용합니다")
        
    speech_result = merge_speech_result(audio_metrics, audio_features)
    
    return predict_attention(speech_result, audience_weight)
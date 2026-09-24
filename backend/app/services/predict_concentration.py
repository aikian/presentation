from typing import Any, List, Optional, Tuple
import statistics
import logging
from collections import deque

from app.core.weights_db import get_weights
from app.services.speech_feature import merge_speech_result

logger = logging.getLogger(__name__)

# 기본 가중치 설정 (청중 설문 피드백에 따라 동적으로 갱신 가능)
# 가중치는 연구 또는 논문을 통해 수정 예정
DEFAULT_WEIGHT: dict[str, Any] = {
    "base_score": 85.0,
    "recovery_per_sec": 0.01,
    
    # 말속도 관련 가중치
    "spm_penalty_weight": 0.5,
    # 최근 20초 중 60% 이상이 빠르거나 느리면 감점
    "spm_window_sec": 20,
    "spm_ratio_threshold": 0.6,
    "spm_penalty_cooldown_sec": 20, 
    
    # 정적 관련 가중치
    "silence_penalty_weight": 0.5,
    "silence_penalty_max_multiplier": 3.0,
    
    # 단조로움 가중치
    "monotone_consecutive_count_limit": 15, # 15초 이상 단조로울 시 감점 
    # 단조로움 이후 환기
    "reengagement_count": 3, # 3초 이상 지속 시 가점
    # 과도한 어조 변화
    "excessive_count": 3,
    # pitch 가중치
    "pitch_weight": 0.5,
    
    # 군말
    "filler_penalty_weight": 0.5,
    
    # 음량 강조
    "db_boost_weight": 0.5
}

DEFAULT_THRESHOLD: dict[str, Any] = {
    # 말속도(동시통역에 적합한 한국어 발화 속도 연구)
    "fast_spm_threshold": 340.0,
    "slow_spm_threshold": 200.0,
    
    # 정적(4초 이상 지속 시 감점) -> 논문: Disrupting the flow: How brief silences in group conversations affect social needs
    "silence_penalty_threshold": 4.0,
    
    # pitch 변동률이 0.15 이하면 단조로움 감점
    "monotone_penalty_threshold": 0.15,
    
    # pitch 변동률이 0.15 이상이면 환기 가점
    "reengagement_pitch_threshold": 0.15,
    
    # pitch 변동률이 0.25 이상이면 과도한 어조 변화로 감점
    "excessive_pitch_threshold": 0.25,
    
    # 최근 60초 동안 군말이 12번 이상 나오면 감점
    "filler_60sec_limit": 12,  
    
    # 음량 강조
    "db_zscore_threshold": 1.0,
    "db_zscore_change_threshold": 1.2,
    
    "max_penalty_per_sec": 5.0
}

# 에러 발생 시 에러 결과 반환
def make_error_result(code: str, message: str) -> dict[str, Any]:
    return {
        "status": "ERROR",
        "error_code": code,
        "message": message,
        "attention_score": None,
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

# pitch 변동률 계산
def calculate_pitch_v(pitches: List[float]) -> Optional[float]:
    
    valid_pitches = [pitch for pitch in pitches if pitch is not None and pitch > 0]
    
    if len(valid_pitches) < 3:
        return None
    
    mean_pitch = statistics.mean(valid_pitches)
    std_pitch = statistics.stdev(valid_pitches)
    
    return (std_pitch / mean_pitch) if mean_pitch > 0 else None

# 최근 SPM 평균
def get_average_spm(spm_data:dict[int, float], sec:int, window: int = 5) -> Optional[float]:
    start = max(0,sec - window + 1)
    end =  sec + 1
    
    spm_values = [spm_data[i] for i in range(start, end) if i in spm_data and spm_data[i] > 0]
    
    if len(spm_values) < 3:
        return None
    
    return statistics.mean(spm_values)

# 최근 pitch 변동
def get_pitch_variation(pitch_data: dict[int, float], sec: int, window: int = 5) -> Optional[float]:
    start = max(0, sec - window + 1)
    
    pitches = [pitch_data[i] for i in range(start, sec + 1) if i in pitch_data and pitch_data[i] > 0]
    
    return calculate_pitch_v(pitches)

# 최근 60초 군말 개수
def get_filler_count_per_min(filler_by_sec: List[dict[str, Any]], sec: int) -> tuple[int, List[str]]:
    
    start = max(0.0, float(sec) - 60.0)
    filler_count = 0
    filler_words: List[str] = []
    
    for filler in filler_by_sec:
        filler_sec = filler["sec"]
        word = filler["word"]
        if start < filler_sec <= sec:
            filler_count += 1
            if word:
                filler_words.append(str(word))
            
    return filler_count, filler_words

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
    
    seconds = speech_result.get("seconds", [])
    spm_data = speech_result.get("spm_data", [])
    silence_data = speech_result.get("silence_data", [])
    silence_penalty_secs = build_silence_penalty_secs(silence_data, threshold["silence_penalty_threshold"], weight["silence_penalty_weight"], weight["silence_penalty_max_multiplier"])
    fillers_by_sec = speech_result.get("fillers_by_sec", [])
    pitch_data = speech_result.get("pitch_data", [])
    norm_db_data = speech_result.get("norm_db_data", [])
    
    if not seconds or not spm_data or not pitch_data or not norm_db_data:
        return make_error_result("NO_DATA", "필수 데이터(seconds)가 존재하지 않습니다")
    if  not spm_data:
        return make_error_result("NO_DATA", "필수 데이터(spm_data)가 존재하지 않습니다")
    if pitch_data:
        return make_error_result("NO_DATA", "필수 데이터(pitch_data)가 존재하지 않습니다")
    if not norm_db_data:
        return make_error_result("NO_DATA", "필수 데이터(norm_db_data)가 존재하지 않습니다")
    
    
    # 초 단위 집중도 저장
    sec_scores: List[dict[str, Any]] = []
    
    # 상태 변수 초기화
    monotone_duration = 0
    reengagement_duration = 0
    excessive_duration = 0
    monotone_detected = False
    
    # 말속도: 최근 구간 내 분류 이력 + 감점 쿨다운
    spm_history: deque = deque()  # (sec, "fast" | "slow" | "normal")
    last_spm_penalty_sec = {"fast": float("-inf"), "slow": float("-inf")}
    
    total_stats = {
        "total_spm_penalty_counts": 0,
        "total_monotone_counts": 0,
        "total_excessive_pitch_counts": 0,
        "total_silence_counts": 0,
        "total_filler_counts": 0,
        "total_reengagement_boost_counts": 0,
        "total_db_boost_counts": 0
    }
    
    # 군말은 '현재 적용 중인 감점 단계(0~3)'로 관리 (단계가 올라갈 때만 추가 감점)
    filler_tier = 0
    
    monotone_threshold = threshold["monotone_penalty_threshold"]
    reengagement_threshold = threshold["reengagement_pitch_threshold"]
    excessive_threshold = threshold["excessive_pitch_threshold"]
                
    monotone_limit = weight["monotone_consecutive_count_limit"]
    reengagement_limit = weight["reengagement_count"]
    excessive_limit = weight["excessive_count"]
    
    base_score = weight["base_score"]
    recovery = weight["recovery_per_sec"]
    running_score = base_score
    
    # 초 단위 평가
    for idx, raw_sec in enumerate(seconds):
        sec = int(raw_sec if raw_sec is not None else idx)
        sec_delta = 0.0
        penalties_applied = []
        boosts_applied = []
        events_applied: List[str] = [] 
    
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
            if valid_count >= 3:
                fast_ratio = sum(1 for _, state in spm_history if state == "fast") / valid_count
                slow_ratio = sum(1 for _, state in spm_history if state == "slow") / valid_count
                
                if (
                    fast_ratio >= weight["spm_ratio_threshold"] 
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
         
        # 단조로움 평가
        pitch_v = get_pitch_variation(pitch_data, sec)
        
        if pitch_v is None:
        
            monotone_duration = 0
            reengagement_duration = 0
            excessive_duration = 0
        
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
            
        # 음량 강조 평가
        current_db = norm_db_data.get(sec, 0.0)
        prev_db = [norm_db_data[i] for i in range(max(0, sec-3), sec) if i in norm_db_data]
            
        if len(prev_db) >= 2:
            prev_avg_db = statistics.mean(prev_db)
            db_change = current_db - prev_avg_db
            
            if current_db >= threshold["db_zscore_threshold"] and db_change >= threshold["db_zscore_change_threshold"]:
                boost = weight["db_boost_weight"]
                sec_delta += boost
                boosts_applied.append(f"음량 강조 가점 (+{boost:.1f})")
                total_stats["total_db_boost_counts"] += 1
                events_applied.append("db_boost")
        
        # 군말 검사
        filler_count, filler_words = get_filler_count_per_min(fillers_by_sec, sec)
        
        if filler_count >= threshold["filler_60sec_limit"]:
            excess_count = filler_count - threshold["filler_60sec_limit"]
            
            if excess_count < 3:
                tier = 1
            elif excess_count < 7:
                tier = 2
            else:
                tier = 3
                
            if tier > filler_tier:
                penalty = weight["filler_penalty_weight"] * (tier - filler_tier)
                sec_delta -= penalty
                unique_words = ", ".join(dict.fromkeys(filler_words))
                penalties_applied.append(f"60초간 군말 과다 ({filler_count}회): {unique_words} (-{penalty:.1f})")
                events_applied.append("filler")
                total_stats["total_filler_counts"] += 1
                
                filler_tier = tier
        else:
            filler_tier = 0
            
        running_score += max(sec_delta, -threshold["max_penalty_per_sec"])
        if running_score < base_score:
            running_score = min(base_score, running_score + recovery)
        elif running_score > base_score:
            running_score = max(base_score, running_score - recovery)
        running_score = max(0.0, min(100.0, running_score))
 
        sec_scores.append({
            "sec": sec,
            "score": round(running_score, 1),
            "penalties": penalties_applied,
            "boosts": boosts_applied,
            "events": events_applied
        })
        
   
    final_score = round(statistics.mean(item["score"] for item in sec_scores), 1)
    
    # 분 단위 결과
    min_score = make_min_timeline(sec_scores)
    
    return {
        "status": "SUCCESS",
        "error_code": None,
        "message": "집중도 추정 성공",
        "attention_score": final_score,
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
    print(audio_metrics)
    return predict_attention(speech_result, audience_weight)
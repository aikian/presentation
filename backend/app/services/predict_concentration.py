from typing import Any, List, Optional, Tuple
import statistics
import logging

from pathlib import Path
from app.services.audio_analyzer import analyze_audio
from app.core.weights_db import get_group_weights
from app.services.survey_analyzer import VALID_GROUPS

logger = logging.getLogger(__name__)

# 기본 가중치 설정 (청중 설문 피드백에 따라 동적으로 갱신 가능)
# 가중치는 연구 또는 논문을 통해 수정 예정
DEFAULT_WEIGHT: dict[str, Any] = {
    "base_score": 85.0,
    "recovery_per_sec": 0.01,
    
    # 말속도 관련 가중치
    "spm_penalty_weight": 0.5,
    
    # 20초 이상 말속도가 빠르거나 느리면 감점
    "fast_spm_consecutive_limit": 20,
    "slow_spm_consecutive_limit": 20,
    
    # 정적 관련 가중치
    "silence_penalty_weight": 0.5,
    
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
    
    # 정적(4초 이상 지속 시 감점) -> 논문: Disrupting tempo: The effect of conversational lapses on affective and cognitive responses
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
    "db_zscore_change_threshold": 1.2
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
         
         
def validate_speech_data(speech_result: Optional[dict[str, Any]]) -> Tuple[Optional[dict[str, Any]], Optional[list], Optional[dict[str, Any]]]:
    if not speech_result:
        return None, None, make_error_result("NO_SPEECH_RESULT", "음성 분석 데이터가 전달되지 않았습니다.")
    
    data = speech_result.get("audio", speech_result)
    
    
    if not data:
        return None, None, make_error_result("NO_DATA", "데이터가 존재하지 않습니다.")
    
    timeline = data.get("timeline", [])
    if not timeline:
        return None, None, make_error_result("NO_DATA", "타임라인이 존재하지 않습니다.")
    
    return data, timeline, None
     
     
# spm 전처리
def preprocess_spm(timeline_list: List[dict[str, Any]]) -> dict[int, float]:
    spm_by_sec: dict[int, float] = {}
    
    for t in timeline_list:
        sec = t.get("sec")
        spm = t.get("spm")
        if sec is None or spm is None:
            continue
        
        try:
            spm_value = float(spm)
        except (TypeError, ValueError):
            continue
        
        if spm_value <= 0:
            continue
        
        spm_by_sec[int(sec)] = spm_value
        
    return spm_by_sec

# 정적 전처리
def preprocess_silences(silence_list: List[dict[str, Any]]) -> List[dict[str, float]]:
    silence_times: List[dict[str, Any]] = []
    
    for s in silence_list:
        start_sec = s.get("start", 0.0)
        end_sec = s.get("end", 0.0)
        duration = s.get("duration", end_sec - start_sec)
        
        if end_sec <= start_sec:
            continue
        
        silence_times.append({
            "start": start_sec,
            "end": end_sec,
            "duration": duration
        })
        
    return silence_times

def build_silence_penalty_secs(silence_data: List[dict[str, float]], min_duration: float) -> dict[int, float]:
    penalty_secs: dict[int, float] = {}
 
    for silence in silence_data:
        if silence["duration"] < min_duration:
            continue
 
        penalty_secs[int(silence["end"])] = silence["duration"]
 
    return penalty_secs
         
# 군말 전처리 
def preprocess_fillers(filler_list: List[dict[str, Any]]) -> List[dict[str, Any]]:
    filler_by_sec: List[dict[str, Any]] = []
    
    for filler in filler_list:
        sec = filler.get("sec")
        word = filler.get("word")
        
        if sec is None:
            continue
        
        filler_by_sec.append({
            "sec": sec,
            "word": word,
        })
        
    return filler_by_sec
 
 # pitch 전처리
def preprocess_pitches(timeline_list: List[dict[str, Any]]) -> dict[int, float]:
    pitch_by_sec: dict[int, float] = {}
    
    for t in timeline_list:
        sec = t.get("sec")
        pitch_hz = t.get("pitch_hz")
        
        if sec is None or pitch_hz is None:
            continue
        
        if pitch_hz <= 0:
            continue
        pitch_by_sec[int(sec)] = pitch_hz
        
    return pitch_by_sec

# dB 전처리
def preprocess_db(timeline_list: List[dict[str, Any]]) -> dict[int, float]:
    norm_db_sec: dict[int, float] = {}
    
    db_list = [item.get("db") for item in timeline_list if item.get("db") is not None]
    db_avg = statistics.mean(db_list) if db_list else 0.0
    db_std = statistics.stdev(db_list) if len(db_list) > 1 else 0.0
    
    for t in timeline_list:
        sec = t.get("sec")
        db = t.get("db")
        if db is None or sec is None:
            continue
        db_norm = (db - db_avg) / db_std if db_std > 0 else 0.0
        norm_db_sec[int(sec)] = db_norm
        
    return norm_db_sec

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
    start = max(0,sec-window)
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
def get_filler_count_last_60sec(filler_by_sec: List[dict[str, Any]], sec: int) -> tuple[int, List[str]]:
    
    start = max(0.0, float(sec) - 60.0)
    filler_count = 0
    filler_words: List[str] = []
    
    for filler in filler_by_sec:
        filler_sec = filler["sec"]
        word = filler["word"]
        if start <= filler_sec <= sec:
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
            "event": event_counts
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
    
    data, timeline, error = validate_speech_data(speech_result)
    if error:
        return error
    
    transcript = data.get("transcript", [])
    transcript_end = transcript[-1].get("end", 0.0) if transcript else 0.0
    timeline_end = timeline[-1].get("end", 0.0) if timeline else 0.0
    duration = max(transcript_end, timeline_end )
    
    if duration <= 0:
        return make_error_result("INVALID_DURATION", "발표 시간을 측정할 수 없습니다")
    
    # 전처리
    spm_data = preprocess_spm(timeline)
    silence_data = preprocess_silences(data.get("silences", []))
    silence_penalty_secs = build_silence_penalty_secs(silence_data, threshold["silence_penalty_threshold"])
    fillers_by_sec = preprocess_fillers(data.get("filler_words", []))
    pitch_data = preprocess_pitches(timeline)
    norm_db_data = preprocess_db(timeline)
    
    # 초 단위 집중도 저장
    sec_scores: List[dict[str, Any]] = []
    
    # 상태 변수 초기화
    monotone_duration = 0
    reengagement_duration = 0
    excessive_duration = 0
    monotone_detected = False
    
    fast_spm_count = 0
    slow_spm_count = 0
    
    previous_spm_sec: Optional[int] = None
    
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
    for idx, item in enumerate(timeline):
        sec = int(item.get("sec", idx))
        sec_delta = 0.0
        penalties_applied = []
        boosts_applied = []
        events_applied: List[str] = [] 
    
        # 말속도
        average_spm = get_average_spm(spm_data, sec)
        
        if average_spm is not None:
            is_continuous = previous_spm_sec is not None and sec == previous_spm_sec + 1
            
            if average_spm > threshold["fast_spm_threshold"]:
                if is_continuous:
                    fast_spm_count += 1
                else:
                    fast_spm_count = 1
                    
                slow_spm_count = 0
                
                if fast_spm_count >= weight["fast_spm_consecutive_limit"]:
                    spm_penalty = weight["spm_penalty_weight"]
                    sec_delta -= spm_penalty
                    penalties_applied.append(f" 빠른 말속도(평균 {average_spm:.1f}SPM) (-{spm_penalty:.1f})")
                    total_stats["total_spm_penalty_counts"] += 1
                    events_applied.append("fast_spm")
                    
                    fast_spm_count = 0
                    
            elif average_spm < threshold["slow_spm_threshold"]:
                if is_continuous:
                    slow_spm_count += 1
                else:
                    slow_spm_count = 1
                    
                fast_spm_count = 0
                
                if slow_spm_count >= weight["slow_spm_consecutive_limit"]:
                    spm_penalty = weight["spm_penalty_weight"]
                    sec_delta -= spm_penalty
                    penalties_applied.append(f"느린 말속도(평균 {average_spm:.1f}SPM) (-{spm_penalty:.1f})")
                    total_stats["total_spm_penalty_counts"] += 1
                    events_applied.append("slow_spm")
                    
                    slow_spm_count = 0
                        
            else:
                fast_spm_count = 0
                slow_spm_count = 0
                
            previous_spm_sec = sec
        
        # 정적 평가
        if sec in silence_penalty_secs:
            duration_s = silence_penalty_secs[sec]
            silence_penalty = weight["silence_penalty_weight"]
            sec_delta -= silence_penalty
            penalties_applied.append(f"{duration_s:.1f}초 정적 감지 (-{silence_penalty:.1f})")
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
        filler_count, filler_words = get_filler_count_last_60sec(fillers_by_sec, sec)
        
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
            
        running_score += sec_delta
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
        "attention_score": final_score,
        "timeline_second": sec_scores,
        "timeline_minute": min_score,
        "total_stats": total_stats,
    }


# 음성 데이터를 분석 모듈에서 받아오는 코드 -> 수정 필요
def analyze_audience(video_path: Path, audience_group: Optional[str]  = None) -> dict[str, Any]:
    audience_weight: Optional[dict[str, Any]] = None
    
    if audience_group:
        audience_group = audience_group.strip().lower()

        if audience_group not in VALID_GROUPS:
            return make_error_result("INVALID_AUDIENCE_GROUP", f"잘못된 audience_group 값입니다: {audience_group}")

        try:
            audience_weight = get_group_weights(audience_group)["weights"]
        except Exception:
            # 가중치 조회에 실패해도 예측 자체는 기본 가중치로 계속 진행
            logger.exception("그룹 가중치 조회 실패, 기본 가중치를 사용합니다: %s", audience_group)

    try:
        audio_result = analyze_audio(video_path)
    except Exception:
        logger.exception("음성 분석 실패: %s", video_path)
        return make_error_result("AUDIO_ANALYSIS_FAILED", "음성 분석 중 오류가 발생했습니다.")

    return predict_attention(audio_result, audience_weight)
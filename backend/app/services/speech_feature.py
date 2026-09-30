from typing import Any, List, Optional
import statistics
import math

def to_float(value: Any) -> Optional[float]:
    try:
        v = float(value)
    except (TypeError, ValueError):
        return None
    
    return v if math.isfinite(v) else None

def merge_speech_result(audio_metrics: dict, audio_features: dict) -> dict:
    
    spm_by_sec = {
        int(item["sec"]): item.get("spm")
        for item in audio_metrics.get("timeline", [])
        if item.get("sec") is not None
    }
    
    timeline = [
        {
            "sec": int(item["sec"]),
            "spm": spm_by_sec.get(int(item["sec"])),
            "pitch_hz": item.get("pitch_hz"),
            "db": item.get("db")
        }
        for item in audio_features.get("timeline", [])
        if item.get("sec") is not None
    ]
    
    silences = audio_features.get("silences", [])
 
    return {
        "duration_sec": audio_metrics.get("duration_sec", 0.0),
        "seconds": [item.get("sec") for item in timeline],
        "spm_data": preprocess_spm(timeline),
        "silence_data": preprocess_silences(silences),
        "pitch_data": preprocess_pitches(timeline),
        "norm_db_data": preprocess_db(timeline)
    }
    
# spm 전처리
def preprocess_spm(timeline_list: List[dict[str, Any]]) -> dict[int, float]:
    spm_by_sec: dict[int, float] = {}
    
    for t in timeline_list:
        sec = t.get("sec")
        spm_value = to_float(t.get("spm"))
        if sec is None or spm_value is None or spm_value <= 0:
            continue
        spm_by_sec[int(sec)] = spm_value
        
    return spm_by_sec

# 정적 전처리
def preprocess_silences(silence_list: List[dict[str, Any]]) -> List[dict[str, float]]:
    silence_times: List[dict[str, Any]] = []
    
    for s in silence_list:
        start_sec = to_float(s.get("start"))
        end_sec = to_float(s.get("end"))
        
        if start_sec is None or end_sec is None or end_sec <= start_sec:
            continue
        
        duration = to_float(s.get("duration"))
        if duration is None:
            duration = end_sec - start_sec
        
        silence_times.append({
            "start": start_sec,
            "end": end_sec,
            "duration": duration
        })
        
    return silence_times

# pitch 전처리
def preprocess_pitches(timeline_list: List[dict[str, Any]]) -> dict[int, float]:
    pitch_by_sec: dict[int, float] = {}
    
    for t in timeline_list:
        sec = t.get("sec")
        pitch_value = to_float(t.get("pitch_hz"))
        if sec is None or pitch_value is None or pitch_value <= 0:
            continue
        pitch_by_sec[int(sec)] = pitch_value
        
    return pitch_by_sec

# dB 전처리
def preprocess_db(timeline_list: List[dict[str, Any]]) -> dict[int, float]:
    raw_db: dict[int, float] = {}
    
    for t in timeline_list:
        sec = t.get("sec")
        db = to_float(t.get("db"))
        if sec is None or db is None:
            continue
        
        raw_db[int(sec)] = db
    
    db_list = list(raw_db.values())
    db_avg = statistics.mean(db_list) if db_list else 0.0
    db_std = statistics.stdev(db_list) if len(db_list) > 1 else 0.0
    
    norm_db_sec: dict[int, Optional[float]] = {}
    for sec, v in raw_db.items():
        norm_db_sec[sec] = (v - db_avg) / db_std if db_std > 0 else 0.0
        
    return norm_db_sec
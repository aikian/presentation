from typing import Any, List, Optional
import statistics

def merge_speech_result(audio_metrics: dict, audio_features: dict) -> dict:
    
    spm_by_sec = {
        item["sec"]: item.get("spm")
        for item in audio_metrics.get("timeline", [])
    }
    
    timeline = [
        {
            "sec": item["sec"],
            "spm": spm_by_sec.get(item["sec"]),
            "pitch_hz": item.get("pitch_hz"),
            "db": item.get("db")
        }
        for item in audio_features.get("timeline", [])
    ]
    
    silences = audio_features.get("silences", [])
    filler_words = audio_metrics.get("filler_words", [])
 
    return {
        "duration_sec": audio_metrics.get("duration_sec", 0.0),
        "seconds": [item.get("sec") for item in timeline],
        "spm_data": preprocess_spm(timeline),
        "silence_data": preprocess_silences(silences),
        "fillers_by_sec": preprocess_fillers(filler_words),
        "pitch_data": preprocess_pitches(timeline),
        "norm_db_data": preprocess_db(timeline)
    }
    
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
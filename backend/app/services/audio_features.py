from pathlib import Path
from typing import Any

import logging
import numpy as np
import librosa

from app.services.audio_analyzer import extract_audio

logger = logging.getLogger(__name__)

SAMPLE_RATE = 16000

# 1초 단위로 결과를 저장
TIMELINE_INTERVAL_SEC = 1.0

# Pitch 분석 범위
PITCH_MIN_HZ = 65.0
PITCH_MAX_HZ = 400.0

# Silence 판정
SILENCE_DB_THRESHOLD = -40.0
MIN_SILENCE_SEC = 0.5

# 음성 분석 frame 설정
FRAME_LENGTH = 2048
HOP_LENGTH = 512

def load_audio(wav_path: Path) -> tuple[np.ndarray, int]:
    y, sr = librosa.load(str(wav_path), sr=SAMPLE_RATE, mono=True)
    
    return y, sr

# 공통으로 사용하는 음성 feature 추출
def extract_audio_feature(y: np.ndarray, sr: int) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    
    rms = librosa.feature.rms(y=y, frame_length=FRAME_LENGTH, hop_length=HOP_LENGTH)[0] 
    rms_db = librosa.amplitude_to_db(rms, ref=1.0, amin=1e-10)
    rms_times = librosa.times_like(rms, sr=sr, hop_length=HOP_LENGTH)
    
    # Pitch
    f0, voiced_flag, voiced_prob = librosa.pyin(
        y,
        fmin=PITCH_MIN_HZ,
        fmax=PITCH_MAX_HZ,
        sr=sr,
        frame_length=FRAME_LENGTH,
        hop_length=HOP_LENGTH
    )
    
    f0 = np.where(
        voiced_flag & (voiced_prob >= 0.7),
        f0,
        np.nan
    )
    
    pitch_times = librosa.times_like(f0, sr=sr, hop_length=HOP_LENGTH)
    
    return rms_db, rms_times, f0, pitch_times
    
# 1초 단위로 pitch 추출    
def extract_pitch(
    f0: np.ndarray,
    pitch_times: np.ndarray,
    duration: float,
    interval_sec: float = TIMELINE_INTERVAL_SEC
) -> list[dict[str, Any]]:
    
    if duration <= 0:
        return []
    
    result: list[dict[str, Any]] = []
    
    for current_sec in np.arange(0.0, duration, interval_sec):
        start_sec = float(current_sec)
        end_sec = min(start_sec + interval_sec, duration)
         
        mask = (
            (pitch_times >= start_sec)
            & (pitch_times < end_sec)
            & np.isfinite(f0)
            & (f0 >= PITCH_MIN_HZ)
            & (f0 <= PITCH_MAX_HZ)
        )
        
        values = f0[mask]
        
        pitch_hz: float | None = None
        
        if values.size > 0:
            
            if values.size >=3:
                lo, hi = np.percentile(values, [5, 95])
                
                values = values[(values >= lo) & (values <= hi)]
            
            if values.size > 0:
                pitch_hz = float(np.median(values))
    
        result.append({
            "sec": round(start_sec, 1),
            "pitch_hz": round(pitch_hz, 1) if pitch_hz is not None else None
        })   
    
    return result 
    
# 1초 단위의 dB 계산
def extract_db(
    rms_db: np.ndarray,
    rms_times: np.ndarray,
    duration: float,
    interval_sec: float = TIMELINE_INTERVAL_SEC
) -> list[dict[str, Any]]:
    
    if duration <= 0:
        return []
    
    result: list[dict[str, Any]] = []
    
    for current_sec in np.arange(0.0, duration, interval_sec):
        start_sec = float(current_sec)
        end_sec = min(start_sec + interval_sec, duration)
        
        mask = (rms_times >= start_sec) & (rms_times < end_sec)
        values = rms_db[mask]    
        values = values[np.isfinite(values)]
        
        representative_db = float(np.median(values)) if values.size > 0 else None
            
        result.append({
            "sec": round(start_sec, 1),
            "db": round(representative_db, 1) if representative_db is not None else None
        })
            
    return result
    
# 정적 계산
def extract_silences(
    pitch: list[dict[str, Any]],
    db: list[dict[str, Any]],
    duration: float,
    silence_db_threshold: float = SILENCE_DB_THRESHOLD,
    min_silence_sec: float = MIN_SILENCE_SEC
) -> list[dict[str, Any]]:
    # pitch와 dB를 사용하여 정적 추출
    
    if duration <= 0 or not pitch or not db:
        return []
    
    db_values = [
        item["db"]
        for item in db
        if item["db"] is not None and np.isfinite(item["db"])
    ]
    
    if not db_values:
        return []
    
    # 파일의 기준 음량을 통해 silence 기준 조정
    base_db = float(np.median(db_values))
    
    relative_threshold = base_db - 15.0
    
    dynamic_threshold = min(
        silence_db_threshold,
        relative_threshold
    )
    
    silence_mask: list[bool] = []
    
    for pitch_item, db_item in zip(pitch, db):
        pitch_hz = pitch_item["pitch_hz"]
        db_value = db_item["db"]
        
        if db_value is None:
            silence_mask.append(True)
            continue
        
        is_silence = (
            pitch_hz is None
            and db_value <= silence_db_threshold
        )
        
        silence_mask.append(is_silence)
        
    if not silence_mask:
        return []

    result: list[dict[str, Any]] = []
    
    start_idx: int | None = None
    
    for idx, is_silence in enumerate(silence_mask):
        
        if is_silence and start_idx is None:
            start_idx = idx
            
        elif not is_silence and start_idx is not None:
            start = float(pitch[start_idx]["sec"])
            end = float(pitch[idx]["sec"])
    
            silence_duration = end - start
        
            if silence_duration >= min_silence_sec:
                result.append({
                    "start": round(start, 1),
                    "end": round(end, 1),
                    "duration": round(silence_duration, 1)
            })
            start_idx = None
            
    if start_idx is not None:
        start = float(pitch[start_idx]["sec"])
        end = duration
        
        silence_duration = end - start
                
        if silence_duration >= min_silence_sec:
            result.append({
                "start": round(start, 1),
                "end": round(end, 1),
                "duration": round(silence_duration, 1)
        })
    
    return result
 
def merge_timeline(pitch: list[dict[str, Any]], db: list[dict[str, Any]]) -> list[dict[str, Any]]:
    
    # sec 기준으로 pitch와 dB 통합
    pitch_by_sec = {item["sec"]: item["pitch_hz"] for item in pitch}       
    db_by_sec = {item["sec"]: item["db"] for item in db}
    
    seconds = sorted(set(pitch_by_sec) | set(db_by_sec))
    
    return [
        {
            "sec": sec,
            "pitch_hz": pitch_by_sec.get(sec),
            "db": db_by_sec.get(sec)
        }
        for sec in seconds
    ]

def analyze_audio_features(video_path: Path) -> dict[str, Any]:
    
    wav_path = extract_audio(video_path)
    if wav_path is None:
        return {
            "timeline": [],
            "silences": []
        }
    
    try:
        y, sr = load_audio(wav_path)
        
        if y.size == 0:
            return {
                "timeline": [],
                "silences": []
            }
            
        duration = len(y) / sr
        
        # 공통 feature 계산
        rms_db, rms_times, f0, pitch_times = extract_audio_feature(y, sr)
        
        # Pitch
        pitch = extract_pitch(f0, pitch_times, duration)
        
        # dB
        db = extract_db(rms_db, rms_times, duration)
        
        # Silence
        silences = extract_silences(pitch, db, duration)
        
        timeline = merge_timeline(pitch, db)
        
        return {
            "timeline": timeline,
            "silences": silences
        }
    
    except Exception as exc:
        logger.warning("오디오 feature 분석 실패: %s", exc)
        return {
            "timeline": [],
            "silences": []
        }
    
    finally:
        wav_path.unlink(missing_ok=True)

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

# 정상적인 음성의 기준 음량
REFERENCE_DB = -20.0

# 임계값에서 2.0 낮은 값까지는 일정 프레임 이상 나올시 정적으로 인식
# -> 작은 음성을 정적으로 인식하는 것응ㄹ 방지
LOW_SILENCE_START_DB = 2.0
# 정적 상태에서 이 값만큼 높은 dB까지는 정적으로 유지
SILENCE_END_DB = 2.0

MIN_SILENCE_SEC = 1.0

SMALL_VOICE_DB_MARGIN = 3.0

MAX_VOICE_RATIO = 0.15

MIN_CONSECUTIVE_VOICE_SEC = 0.15
MIN_VOICE_TO_END_SILENCE_SEC  = 0.10

SILENCE_THRESHOLD_OFFSET_DB = 3.5

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
    
    valid_pitch = (
        voiced_flag
        & np.isfinite(voiced_prob) 
        & (voiced_prob >= 0.7)
        & np.isfinite(f0)
        & (f0 >= PITCH_MIN_HZ)
        & (f0 <= PITCH_MAX_HZ)
    )
    
    f0 = np.where(
        valid_pitch,
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
    
def calculate_silence_threshold(rms_db: np.ndarray) -> float:
    valid_db = rms_db[np.isfinite(rms_db)]

    if valid_db.size == 0:
        return SILENCE_DB_THRESHOLD
    
    p0, p25, p50, p75, p90, p95, p100 = np.percentile(
        valid_db,
        [0, 25, 50, 75, 90, 95, 100]
    )
    
    stats = {
        "p0": p0,
        "p25": p25,
        "p50": p50,
        "p75": p75,
        "p90": p90,
        "p95": p95,
        "p100": p100,
    }
    
    # 1. 전체적으로 작은 파일
    if p95 < -30:
        base_db = p50 - 3.0

    # 2. 정적 중심 파일
    elif (p100 - p75) < 3.0:
        base_db = p50

    # 3. 음성과 정적이 비교적 잘 분리된 파일
    elif (p95 - p75) > 10.0:
        base_db = p75

    # 4. 일반적인 경우
    else:
        base_db = p25

    base_db = float(np.clip(base_db, -60.0, -20.0))

    print(
        f"P0={stats['p0']:.1f}, "
        f"P25={stats['p25']:.1f}, "
        f"P50={stats['p50']:.1f}, "
        f"P75={stats['p75']:.1f}, "
        f"P95={stats['p95']:.1f}, "
        f"P100={stats['p100']:.1f}"
    )
    
    return base_db

def find_max_consecutive_voice_frames(voice_mask: np.ndarray) -> int:
    max_consecutive = 0
    current_consecutive = 0

    for is_voice in voice_mask:
        if is_voice:
            current_consecutive += 1
            max_consecutive = max(max_consecutive, current_consecutive)
        else:
            current_consecutive = 0

    return max_consecutive

# 정적 계산
def extract_silences(
    rms_db: np.ndarray,
    rms_times: np.ndarray,
    duration: float,
    min_silence_sec: float = MIN_SILENCE_SEC
) -> list[dict[str, Any]]:
    # dB를 사용하여 정적 추출
    
    if duration <= 0 or rms_db.size == 0:
        return []
    
    valid = np.isfinite(rms_db)
    
    if not np.any(valid):
        return []
    
    frame_duration = HOP_LENGTH / SAMPLE_RATE
    adaptive_threshold= calculate_silence_threshold(rms_db)
    
    # 정적 상태에서 이 값까지는 정적으로 유지
    silence_end_threshold = adaptive_threshold + SILENCE_END_DB
    silence_candidates: list[dict[str, float]] = []
    
    start_time: float | None = None
    is_silence = False
    
    start_silence_frames = 0
    
    # silence 종료 후보
    end_voice_start_time: float | None = None
    end_voice_frames = 0
    
    min_silence_start_frames = int(np.ceil(MIN_VOICE_TO_END_SILENCE_SEC * SAMPLE_RATE / HOP_LENGTH))
    min_silence_end_frames = int(np.ceil(MIN_VOICE_TO_END_SILENCE_SEC * SAMPLE_RATE / HOP_LENGTH))
    
    for idx, db in enumerate(rms_db):
        
        if not np.isfinite(db):
            continue
        
        current_time = float(rms_times[idx])
        
        if not is_silence:
            if db <= adaptive_threshold:
                if adaptive_threshold - LOW_SILENCE_START_DB < db:
                    start_silence_frames += 1
                
                    if start_silence_frames >= min_silence_start_frames:
                        is_silence = True
                        start_time = (current_time - (start_silence_frames - 1) * frame_duration)

                        end_voice_start_time = None
                        end_voice_frames = 0
                else:
        
                    is_silence = True
                    start_time = current_time

                    start_silence_frames = 0
                    end_voice_start_time = None
                    end_voice_frames = 0

            else:
                start_silence_frames = 0
            
        else:
            if db > silence_end_threshold:
                
                if end_voice_frames == 0:
                    end_voice_start_time = current_time
                    
                end_voice_frames += 1
                
                if end_voice_frames >= min_silence_end_frames:

                    end_time = (
                        end_voice_start_time
                        if end_voice_start_time is not None
                        else current_time
                    )
                    
                    if start_time is not None:
                        silence_duration = end_time - start_time
                
                        if silence_duration >= min_silence_sec:
                            silence_candidates.append({
                                "start": start_time,
                                "end": end_time,
                                "duration": silence_duration
                            })
                
                    is_silence = False
                    start_time= None
                    
                    end_voice_start_time = None
                    end_voice_frames = 0
            
            else:
                end_voice_start_time = None
                end_voice_frames = 0
            
    if is_silence and start_time is not None:
        end_time = float(duration)
        silence_duration = end_time - start_time
                
        if silence_duration >= min_silence_sec:
            silence_candidates.append({
                "start": start_time,
                "end": end_time,
                "duration": silence_duration
            })
            
    voice_threshold = adaptive_threshold - SMALL_VOICE_DB_MARGIN

    print(f"adaptive silence threshold: {adaptive_threshold:.1f} dB")
    print(f"silence end threshold: {silence_end_threshold:.1f} dB")
    print(f"voice threshold: {voice_threshold:.1f} dB")
    print(f"max voice ratio: {MAX_VOICE_RATIO:.2f}")
    print(f"min consecutive voice: {MIN_CONSECUTIVE_VOICE_SEC:.2f}s")
    
    result: list[dict[str, Any]] = []
    
    for idx, item in enumerate(silence_candidates, start=1):
        
        if item["duration"] >= 2.0:
            result.append({
                "start": round(item["start"], 1),
                "end": round(item["end"], 1),
                "duration": round(item["duration"], 1)
            })
        
    print(f"silence count: {len(result)}")
    for idx, item in enumerate(result, start=1):
        print(
            f"{idx}. " 
            f"{item['start']:.1f} ~ {item['end']:.1f} "
            f"({item['duration']:.1f}s) "
            f"[{int(item['start'] // 60):02d}:{item['start'] % 60:04.1f} ~ "
            f"{int(item['end'] // 60):02d}:{item['end'] % 60:04.1f}]"
        )
        
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
        silences = extract_silences(rms_db, rms_times, duration)
        
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

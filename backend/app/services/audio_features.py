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
SILENCE_DB_THRESHOLD = -32.0

# 정적 상태에서 이 값만큼 높은 dB까지는 정적으로 유지
SILENCE_END_DB = 1.0

MIN_SILENCE_SEC = 1.5

# 정적 중 소리 비율이 0.15이상일 경우 정적 제외
MAX_VOICE_RATIO = 0.15

# 정적 중 소리가 연속으로 0.15 동안 나올시 정적에서 제외
MIN_CONSECUTIVE_VOICE_SEC = 0.15

# silence 시작/종료 시 debounce
MIN_SILENCE_START_SEC = 0.20
MIN_SILENCE_END_SEC = 0.12

MIN_CLUSTER_SEPARATION_DB = 8.0

SILENCE_ONLY_DB = -40.0

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
            
            if values.size >= 3:
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
    
    # dB 히스토그램에서 정적과 정적이 아닌 구간으로 분리하는 경계값을 Otsu 방식으로 구함
    hist, bin_edges = np.histogram(valid_db, bins=200)
    hist = hist.astype(np.float64)
    total = hist.sum()
    bin_centers = (bin_edges[:-1] + bin_edges[1:]) / 2.0
    
    sum_total = np.sum(hist * bin_centers)
    sum_bg = 0.0
    weight_bg = 0.0
    max_variance = -1.0
    best_threshold: float | None = None
    best_separation = 0.0
    
    for i in range(len(hist)):
        weight_bg += hist[i]
        if weight_bg == 0:
            continue
        weight_fg = total - weight_bg
        if weight_fg == 0:
            break
        
        sum_bg += hist[i] * bin_centers[i]
        mean_bg = sum_bg / weight_bg
        mean_fg = (sum_total - sum_bg) / weight_fg
        
        variance_between = weight_bg * weight_fg * (mean_bg - mean_fg) ** 2

        if variance_between > max_variance:
            max_variance = variance_between
            best_threshold = float(bin_centers[i])
            best_separation = float(mean_fg - mean_bg)
    
    # 음성에 정적이 없거나 정적만 있을 때 실행
    if best_threshold is None or best_separation < MIN_CLUSTER_SEPARATION_DB:
        median_db = float(np.median(valid_db))
        
        # 전체가 정적
        if median_db <= SILENCE_ONLY_DB:
            threshold = float(np.max(valid_db)) + 2.0
            print(f"[전체무음] threshold={threshold:.1f} dB")
            return threshold
        
        # 정적이 없음
        threshold = float(np.min(valid_db)) - 1.0
        print(f"[전체발화] threshold={threshold:.1f} dB")
        return threshold

    adaptive_threshold = float(np.clip(best_threshold, -60.0, -28.0))
    print(f"separation={best_separation:.1f} dB, threshold={adaptive_threshold:.1f} dB")
    
    return adaptive_threshold

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
    f0: np.ndarray,
    pitch_times: np.ndarray,
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
    
    is_silence = False
    
    # 정적 상태에서 이 값까지는 정적으로 유지
    silence_end_threshold = adaptive_threshold + SILENCE_END_DB
    silence_candidates: list[dict[str, float]] = []
    
    # silence 시작 후보
    silence_start_candidate: float | None = None
    silence_start_frames = 0
    
    # silence 종료 후보
    silence_end_candidate: float | None = None
    silence_end_frames  = 0
    
    min_silence_start_frames = np.ceil(MIN_SILENCE_START_SEC  / frame_duration)
    min_silence_end_frames = np.ceil(MIN_SILENCE_END_SEC  / frame_duration)
    
    start_time: float | None = None
    current_time: float | None = None
    
    for idx, db in enumerate(rms_db):
        
        if not np.isfinite(db):
            continue
        
        current_time = float(rms_times[idx])
        
        # 해당 프레임에 유효한 목소리 피치가 존재하는지 확인
        f0_val = f0[idx]
        has_pitch = np.isfinite(f0_val) and (PITCH_MIN_HZ <= f0_val <= PITCH_MAX_HZ)
        
        # 음성 프레임 판정: dB가 높거나 목소리 피치가 감지되면 발화 중으로 판단
        is_voice_frame = (db > adaptive_threshold) or has_pitch
        
        if not is_silence:
            if not is_voice_frame:
                
                if silence_start_frames == 0:
                    silence_start_candidate = current_time
                                        
                silence_start_frames += 1
                        
                if silence_start_frames >= min_silence_start_frames:
                    is_silence = True
                    start_time = silence_start_candidate 
                    
                    silence_start_candidate = None
                    silence_start_frames = 0
                    
                    silence_end_candidate = None
                    silence_end_frames = 0
                    
            else:
                silence_start_candidate = None
                silence_start_frames = 0
            
        else:
            
            # 정적 상태: 소리가 크거나(종료 임계값 초과) OR 피치가 다시 감지되면 정적 종료 후보로 인정
            is_end_frame = (db > silence_end_threshold) or has_pitch
            if is_end_frame:
                
                if silence_end_frames == 0:
                    silence_end_candidate = current_time
                    
                silence_end_frames += 1
                
                if silence_end_frames >= min_silence_end_frames:
                    end_time = silence_end_candidate
                    
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

                    silence_end_candidate = None
                    silence_end_frames = 0
                
            else:
                silence_end_candidate = None
                silence_end_frames = 0
                
    if is_silence and start_time is not None:
        end_time = float(duration)
        silence_duration = end_time - start_time
                
        if silence_duration >= min_silence_sec:
            silence_candidates.append({
                "start": start_time,
                "end": end_time,
                "duration": silence_duration
            })
            
    voice_threshold = adaptive_threshold - SILENCE_END_DB

    print(f"adaptive silence threshold: {adaptive_threshold:.1f} dB")
    print(f"silence end threshold: {silence_end_threshold:.1f} dB")
    print(f"voice threshold: {voice_threshold:.1f} dB")
    
    result: list[dict[str, Any]] = []
    
    for idx, item in enumerate(silence_candidates, start=1):
        mask  = (
            (rms_times >= item["start"])
            & (rms_times < item["end"])
            & np.isfinite(rms_db)
        )

        db_segment = rms_db[mask]
        f0_segment = f0[mask]
    
        if db_segment.size == 0:
            continue
        
        is_voice_db = db_segment >= voice_threshold
        is_voice_pitch = (
            np.isfinite(f0_segment)
            & (f0_segment >= PITCH_MIN_HZ)
            & (f0_segment <= PITCH_MAX_HZ)
        )
        voice_mask = is_voice_db | is_voice_pitch
        
        voice_frames = int(np.sum(voice_mask))
        voice_ratio = voice_frames / db_segment.size
        
        max_consecutive_frames  = find_max_consecutive_voice_frames(voice_mask)
        max_consecutive_sec  = max_consecutive_frames * frame_duration

        has_voice_ratio = voice_ratio > MAX_VOICE_RATIO
        has_continuous_voice = max_consecutive_sec >= MIN_CONSECUTIVE_VOICE_SEC
        has_sound = has_voice_ratio or (max_consecutive_frames >= 6 and has_continuous_voice)
        
        print(
            f"{idx}. " 
            f"{item['start']:.1f} ~ {item['end']:.1f} "
            f"({item['duration']:.1f}s) "
            f"[{int(item['start'] // 60):02d}:{item['start'] % 60:04.1f} ~ "
            f"{int(item['end'] // 60):02d}:{item['end'] % 60:04.1f}]"
        )
        print(f"   voice_ratio = {voice_ratio:.2f}, max_consecutive = {max_consecutive_sec:.2f}s")
           
        if has_sound:
            print("   -> 작은 음성 포함, silence 제외")
            continue

        print("   -> 최종 silence")
        
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
        silences = extract_silences(rms_db, rms_times, f0, pitch_times, duration)
        
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

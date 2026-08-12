"""오디오 기반 발화 분석. Whisper 전사 + VAD 침묵 + 피치 변동."""
import logging
import re
import subprocess
import tempfile
from pathlib import Path
from typing import Any

import numpy as np

from app.core.config import settings

logger = logging.getLogger(__name__)

SAMPLE_RATE = 16000

# 한글 음절 블록. 말 속도(SPM) 계산 단위로 사용한다.
HANGUL_SYLLABLE = re.compile(r"[가-힣]")

# 필러워드 사전. 팀 리뷰로 조정하는 항목이라 모듈 상단에 모아둔다.
# 단독으로 쓰일 때만 필러로 보는 단어와, 붙어 있어도 필러인 단어를 나눈다.
FILLER_STANDALONE = {
    "어", "음", "아", "에", "그", "저", "뭐", "좀",
}
FILLER_PHRASES = {
    "그니까", "그러니까", "그니깐", "인제", "이제", "약간",
    "뭐랄까", "어떻게 보면", "아시다시피", "그래서 인제",
}

MIN_SILENCE_SEC = 2.0  # 이 이상 이어지면 "긴 침묵"으로 집계

_model = None


def _get_model():
    """Whisper 모델 지연 로딩. 첫 호출에서만 가중치를 내려받는다."""
    global _model
    if _model is None:
        from faster_whisper import WhisperModel

        _model = WhisperModel(
            settings.whisper_model,
            device="cpu",
            compute_type="int8",
        )
    return _model


def extract_audio(video_path: Path) -> Path | None:
    """ffmpeg로 16kHz 모노 wav 추출. 오디오 트랙이 없으면 None."""
    out = Path(tempfile.gettempdir()) / f"{video_path.stem}_audio.wav"
    cmd = [
        "ffmpeg", "-nostdin", "-loglevel", "error", "-y",
        "-i", str(video_path),
        "-vn", "-ac", "1", "-ar", str(SAMPLE_RATE),
        "-f", "wav", str(out),
    ]
    try:
        subprocess.run(cmd, check=True, capture_output=True, timeout=600)
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError) as exc:
        logger.warning("오디오 추출 실패: %s", exc)
        return None

    if not out.exists() or out.stat().st_size < 1024:
        return None
    return out


def _count_syllables(text: str) -> int:
    return len(HANGUL_SYLLABLE.findall(text))


def _count_fillers(segments: list[dict]) -> tuple[int, dict[str, int]]:
    """단어 단위 토큰에서 필러워드를 센다."""
    counts: dict[str, int] = {}

    full_text = " ".join(seg["text"] for seg in segments)
    for phrase in FILLER_PHRASES:
        n = full_text.count(phrase)
        if n:
            counts[phrase] = counts.get(phrase, 0) + n

    for seg in segments:
        for word in seg.get("words", []):
            token = word.strip().strip(".,?!~…\"'")
            if token in FILLER_STANDALONE:
                counts[token] = counts.get(token, 0) + 1

    return sum(counts.values()), counts


def _silence_stats(segments: list[dict], duration: float) -> tuple[float, int, list[dict]]:
    """발화 구간 사이의 빈 시간을 침묵으로 본다. Whisper VAD가 걸러준 구간 기준."""
    if not segments:
        return 1.0, 0, []

    speech_sec = sum(seg["end"] - seg["start"] for seg in segments)
    silence_ratio = max(0.0, 1.0 - speech_sec / duration) if duration > 0 else 0.0

    long_gaps: list[dict] = []
    prev_end = segments[0]["end"]
    for seg in segments[1:]:
        gap = seg["start"] - prev_end
        if gap >= MIN_SILENCE_SEC:
            long_gaps.append({"start": round(prev_end, 1), "sec": round(gap, 1)})
        prev_end = seg["end"]

    return silence_ratio, len(long_gaps), long_gaps[:10]


def _pitch_variation(wav_path: Path) -> tuple[float, float, float]:
    """유성 구간 F0의 변동계수(CV)·중앙값·표준편차(Hz)를 반환. CV가 낮으면 단조로운 억양."""
    try:
        import librosa

        y, sr = librosa.load(str(wav_path), sr=SAMPLE_RATE, mono=True)
        if y.size < sr:
            return 0.0, 0.0, 0.0

        f0 = librosa.yin(y, fmin=65, fmax=400, sr=sr, frame_length=2048)

        # 무성/잡음 구간 제거: 에너지가 충분한 프레임만 남긴다.
        rms = librosa.feature.rms(y=y, frame_length=2048, hop_length=512)[0]
        n = min(len(f0), len(rms))
        f0, rms = f0[:n], rms[:n]
        voiced = f0[(rms > np.percentile(rms, 40)) & np.isfinite(f0)]
        if voiced.size < 10:
            return 0.0, 0.0, 0.0

        # 상하위 5%는 옥타브 오검출이라 자른다.
        lo, hi = np.percentile(voiced, [5, 95])
        voiced = voiced[(voiced >= lo) & (voiced <= hi)]
        if voiced.size < 10 or float(np.mean(voiced)) <= 0:
            return 0.0, 0.0, 0.0

        std = float(np.std(voiced))
        return std / float(np.mean(voiced)), float(np.median(voiced)), std
    except Exception as exc:
        logger.warning("피치 분석 실패: %s", exc)
        return 0.0, 0.0, 0.0


def analyze_audio(video_path: Path) -> dict[str, Any]:
    """영상에서 오디오를 뽑아 발화 지표를 계산한다. 실패해도 예외를 올리지 않는다."""
    empty = {
        "speech_available": False,
        "speech_rate_spm": 0.0,
        "filler_count": 0,
        "filler_per_min": 0.0,
        "filler_detail": {},
        "audio_silence_ratio": 0.0,
        "long_silence_count": 0,
        "long_silences": [],
        "pitch_cv": 0.0,
        "pitch_median_hz": 0.0,
        "pitch_std_hz": 0.0,
        "transcript": "",
        "segments": [],
        "speech_duration_sec": 0.0,
        "duration_sec": 0.0,
    }

    wav = extract_audio(video_path)
    if wav is None:
        return empty

    try:
        model = _get_model()
        raw_segments, info = model.transcribe(
            str(wav),
            language="ko",
            vad_filter=True,
            vad_parameters={"min_silence_duration_ms": 500},
            word_timestamps=True,
            beam_size=1,
        )

        segments: list[dict] = []
        for seg in raw_segments:
            segments.append({
                "start": seg.start,
                "end": seg.end,
                "text": seg.text.strip(),
                "words": [w.word for w in (seg.words or [])],
            })

        if not segments:
            return empty

        duration = float(getattr(info, "duration", 0.0)) or segments[-1]["end"]
        transcript = " ".join(seg["text"] for seg in segments).strip()

        speech_sec = sum(seg["end"] - seg["start"] for seg in segments)
        syllables = _count_syllables(transcript)
        speech_rate = (syllables / speech_sec * 60) if speech_sec > 0 else 0.0

        filler_count, filler_detail = _count_fillers(segments)
        filler_per_min = (filler_count / duration * 60) if duration > 0 else 0.0

        silence_ratio, long_count, long_gaps = _silence_stats(segments, duration)
        pitch_cv, pitch_median, pitch_std = _pitch_variation(wav)

        return {
            "speech_available": True,
            "speech_rate_spm": round(speech_rate, 1),
            "filler_count": filler_count,
            "filler_per_min": round(filler_per_min, 2),
            "filler_detail": filler_detail,
            "audio_silence_ratio": round(silence_ratio, 3),
            "long_silence_count": long_count,
            "long_silences": long_gaps,
            "pitch_cv": round(pitch_cv, 3),
            "pitch_median_hz": round(pitch_median, 1),
            "pitch_std_hz": round(pitch_std, 1),
            "transcript": transcript[:5000],
            # 공유 스키마의 audio.transcript[]로 나가는 원본. 문장 병합 없이 Whisper 세그먼트 그대로 둔다.
            "segments": [
                {"start": round(s["start"], 1), "end": round(s["end"], 1), "text": s["text"]}
                for s in segments
            ],
            "speech_duration_sec": round(speech_sec, 1),
            "duration_sec": round(duration, 1),
        }
    except Exception as exc:
        logger.warning("음성 분석 실패: %s", exc)
        return empty
    finally:
        wav.unlink(missing_ok=True)

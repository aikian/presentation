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

# 피치·음량 분석 프레임. hop 512 = 프레임 하나가 32ms이므로 1초에 31.25개.
FRAME_LENGTH = 2048
HOP_LENGTH = 512

# 한글 음절 블록. 말 속도(SPM) 계산 단위로 사용한다.
HANGUL_SYLLABLE = re.compile(r"[가-힣]")

# 필러워드 사전. 팀 리뷰로 조정하는 항목이라 모듈 상단에 모아둔다.
# 단독으로 쓰일 때만 필러로 보는 단어와, 붙어 있어도 필러인 단어를 나눈다.
FILLER_STANDALONE = {
    "어", "음", "아", "에", "저", "뭐", "좀",
}
FILLER_PHRASES = {
    "그니까", "그러니까", "그니깐", "인제", "이제", "약간",
    "뭐랄까", "어떻게 보면", "아시다시피", "그래서 인제",
}

MIN_SILENCE_SEC = 2.0  # 이 이상 이어지면 "긴 침묵"으로 집계

# Whisper 환각 방어.
# 조용하거나 음악만 있는 구간에서 Whisper가 영상 아웃트로 문구를 지어내거나 같은 문장을
# 반복하는 일이 있다(Koenecke 등, 2024). 세그먼트 신뢰도 값만으로는 잘 못 가려내므로
# (1) 한글 없음 (2) 아웃트로 문구 (3) 같은 문장 연속 반복 (4) 한 단어가 대부분
# (5) 신뢰도가 아주 낮음, 순서로 걸러낸다. 걸러낸 내역은 transcript_quality에 남긴다.
HALLUCINATION_PHRASES = (
    "시청해주셔서감사합니다", "시청해주셔서고맙습니다", "끝까지시청해주셔서",
    "구독과좋아요", "좋아요와구독", "구독좋아요알림설정",
    "다음영상에서만나요", "다음영상에서뵙겠습니다",
    "자막제작", "한글자막", "자막by",
)
REPEAT_SEGMENT_LIMIT = 3      # 같은 문장이 이 횟수 이상 연속되면 세 번째부터 버린다
REPEAT_WORD_RATIO = 0.6       # 세그먼트 단어의 이 비율 이상이 한 단어면 지어낸 것으로 본다
MIN_REPEAT_WORDS = 6          # 그 판정은 단어가 이 개수 이상일 때만 한다
NO_SPEECH_PROB_LIMIT = 0.8    # 이 값을 넘고
AVG_LOGPROB_LIMIT = -1.0      # 이 값보다 낮으면(둘 다) 버린다. 보조 기준.
MIN_SPEECH_RATIO = 0.05       # 걸러낸 뒤 발화가 영상 길이의 이 비율보다 적으면 음성 분석 불가
MAX_SYLLABLES_PER_SEC = 12.0  # 사람이 낼 수 없는 속도면 전사가 깨진 것으로 본다

_NORMALIZE_RE = re.compile(r"[\s.,?!~…\"'\-]")


def _normalize_text(text: str) -> str:
    return _NORMALIZE_RE.sub("", text)


def _dominant_word_ratio(text: str) -> float:
    words = text.split()
    if len(words) < MIN_REPEAT_WORDS:
        return 0.0
    return max(words.count(w) for w in set(words)) / len(words)


def _filter_hallucinations(segments: list[dict]) -> tuple[list[dict], dict[str, int]]:
    """환각으로 보이는 세그먼트를 버리고, 사유별 개수를 돌려준다."""
    kept: list[dict] = []
    dropped = {
        "no_hangul": 0, "outro_phrase": 0, "repeated_segment": 0,
        "repeated_word": 0, "low_confidence": 0,
    }
    prev_norm = None
    repeat_run = 0

    for seg in segments:
        text = seg.get("text", "")
        norm = _normalize_text(text)

        if norm == prev_norm:
            repeat_run += 1
        else:
            repeat_run = 0
            prev_norm = norm

        if not HANGUL_SYLLABLE.search(text):
            dropped["no_hangul"] += 1
            continue
        if any(phrase in norm for phrase in HALLUCINATION_PHRASES):
            dropped["outro_phrase"] += 1
            continue
        if repeat_run >= REPEAT_SEGMENT_LIMIT - 1:
            dropped["repeated_segment"] += 1
            continue
        if _dominant_word_ratio(text) >= REPEAT_WORD_RATIO:
            dropped["repeated_word"] += 1
            continue
        no_speech = seg.get("no_speech_prob")
        logprob = seg.get("avg_logprob")
        if (
            no_speech is not None and logprob is not None
            and no_speech > NO_SPEECH_PROB_LIMIT and logprob < AVG_LOGPROB_LIMIT
        ):
            dropped["low_confidence"] += 1
            continue
        kept.append(seg)

    return kept, dropped


def _speech_plausibility(segments: list[dict], duration: float) -> str | None:
    """전사가 쓸 만한지 본다. 문제가 있으면 사유 문자열, 없으면 None."""
    if not segments:
        return "no_speech_after_filter"
    speech_sec = sum(seg["end"] - seg["start"] for seg in segments)
    if duration > 0 and speech_sec / duration < MIN_SPEECH_RATIO:
        return "too_little_speech"
    syllables = sum(_count_syllables(seg.get("text", "")) for seg in segments)
    if speech_sec > 0 and syllables / speech_sec > MAX_SYLLABLES_PER_SEC:
        return "implausible_rate"
    return None

# 이웃한 초 사이 피치 변화가 이 비율 미만이면 억양이 평평한 것으로 본다.
MONOTONE_THRESHOLD = 0.05

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


TOKEN_STRIP = " .,?!~…\"'"

# FILLER_PHRASES 중 가장 긴 표현이 몇 단어인지. 연속 토큰을 몇 개까지 이어붙여 볼지 정한다.
_MAX_PHRASE_WORDS = max(len(p.split()) for p in FILLER_PHRASES)


def _count_fillers(segments: list[dict]) -> tuple[int, dict[str, int], list[dict]]:
    """단어 토큰을 훑어 필러워드를 센다. 발화 시각도 함께 남긴다.

    Whisper 토큰은 " 그"처럼 앞에 공백이 붙어 오므로 양쪽을 다듬어 비교한다.
    "어떻게 보면"처럼 토큰 두 개에 걸치는 표현이 있어 연속 토큰을 이어붙여 보고,
    긴 표현을 먼저 맞춘다. "그"는 "그 이유는"처럼 정상적인 관형사 용법과
    자동으로 구분하기 어려워 단독 군말 사전에서는 제외한다.
    """
    counts: dict[str, int] = {}
    occurrences: list[dict] = []

    tokens = [
        (w["text"].strip(TOKEN_STRIP), w["start"])
        for seg in segments
        for w in seg.get("words", [])
    ]
    tokens = [(text, start) for text, start in tokens if text]

    i = 0
    while i < len(tokens):
        matched_word = None
        matched_span = 0

        for span in range(min(_MAX_PHRASE_WORDS, len(tokens) - i), 0, -1):
            candidate = " ".join(text for text, _ in tokens[i:i + span])
            if candidate in FILLER_PHRASES or (span == 1 and candidate in FILLER_STANDALONE):
                matched_word, matched_span = candidate, span
                break

        if matched_word is None:
            i += 1
            continue

        counts[matched_word] = counts.get(matched_word, 0) + 1
        occurrences.append({"sec": round(tokens[i][1], 1), "word": matched_word})
        i += matched_span

    return sum(counts.values()), counts, occurrences


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


def _pitch_frames(wav_path: Path) -> tuple[Any, Any] | None:
    """F0와 음량을 프레임 단위로 계산한다.

    yin이 무거워서(14분 영상 기준 수십 초) 한 번만 돌리고
    피치 통계와 시간축이 그 결과를 나눠 쓴다.
    """
    try:
        import librosa

        y, sr = librosa.load(str(wav_path), sr=SAMPLE_RATE, mono=True)
        if y.size < sr:
            return None

        f0 = librosa.yin(y, fmin=65, fmax=400, sr=sr, frame_length=FRAME_LENGTH, hop_length=HOP_LENGTH)
        rms = librosa.feature.rms(y=y, frame_length=FRAME_LENGTH, hop_length=HOP_LENGTH)[0]
        n = min(len(f0), len(rms))
        return f0[:n], rms[:n]
    except Exception as exc:
        logger.warning("피치 분석 실패: %s", exc)
        return None


def _pitch_variation(f0, rms) -> tuple[float, float, float]:
    """유성 구간 F0의 변동계수(CV)·중앙값·표준편차(Hz)를 반환. CV가 낮으면 단조로운 억양."""
    # 무성/잡음 구간 제거: 에너지가 충분한 프레임만 남긴다.
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


def _spm_by_sec(segments: list[dict]) -> dict[int, float]:
    """초 → 그 초가 속한 발화의 말속도(SPM). 발화 밖의 초는 담지 않는다."""
    table: dict[int, float] = {}
    for seg in segments:
        span = seg["end"] - seg["start"]
        if span <= 0:
            continue
        spm = round(_count_syllables(seg["text"]) / span * 60, 1)
        for sec in range(int(seg["start"]), int(np.ceil(seg["end"]))):
            table[sec] = spm
    return table


def _monotone_ratio(timeline: list[dict]) -> float | None:
    """이웃한 두 초 사이 피치가 거의 안 바뀐 비율. 높을수록 단조로운 억양이다."""
    pairs = 0
    flat = 0
    for prev, cur in zip(timeline, timeline[1:]):
        if cur["sec"] - prev["sec"] != 1.0:
            continue
        a, b = prev["pitch_hz"], cur["pitch_hz"]
        if not a or not b:
            continue
        pairs += 1
        if abs(b - a) / a < MONOTONE_THRESHOLD:
            flat += 1

    return round(flat / pairs, 3) if pairs else None


def _build_timeline(f0, rms, segments: list[dict], duration: float) -> list[dict]:
    """1초 구간마다 말속도·피치·음량을 담은 항목을 만든다.

    스키마 규약: 무음 구간의 spm과 무성음 구간의 pitch_hz는 0이 아니라 null.
    db는 항상 값이 있어야 한다(조용해도 배경 소음 수준이 측정된다).
    """
    frames_per_sec = SAMPLE_RATE / HOP_LENGTH
    total = len(rms)
    spm_table = _spm_by_sec(segments)
    voiced_floor = np.percentile(rms, 40)

    timeline = []
    for sec in range(int(duration)):
        lo = int(sec * frames_per_sec)
        hi = min(int((sec + 1) * frames_per_sec), total)
        if lo >= hi:
            break

        bin_rms, bin_f0 = rms[lo:hi], f0[lo:hi]

        # dBFS: 진폭 1.0이 0dB. 완전 무음일 때 log가 발산하지 않게 바닥을 둔다.
        mean_rms = max(float(np.mean(bin_rms)), 1e-6)
        db = round(float(20 * np.log10(mean_rms)), 1)

        voiced = bin_f0[(bin_rms > voiced_floor) & np.isfinite(bin_f0)]
        pitch = round(float(np.mean(voiced)), 1) if voiced.size else None

        timeline.append({
            "sec": float(sec),
            "spm": spm_table.get(sec),
            "pitch_hz": pitch,
            "db": db,
        })

    return timeline


def analyze_audio(video_path: Path) -> dict[str, Any]:
    """영상에서 오디오를 뽑아 발화 지표를 계산한다. 실패해도 예외를 올리지 않는다."""
    empty = {
        "speech_available": False,
        "speech_rate_spm": 0.0,
        "filler_count": 0,
        "filler_per_min": 0.0,
        "filler_detail": {},
        "filler_words": [],
        "timeline": [],
        "audio_silence_ratio": 0.0,
        "long_silence_count": 0,
        "long_silences": [],
        "pitch_cv": 0.0,
        "pitch_median_hz": 0.0,
        "pitch_std_hz": 0.0,
        "monotone_ratio": None,
        "transcript": "",
        "segments": [],
        "speech_duration_sec": 0.0,
        "duration_sec": 0.0,
        # 전사 품질. 걸러낸 세그먼트 수와 음성 분석을 포기한 사유를 남긴다.
        "transcript_quality": None,
    }

    def unavailable(status: str, quality: dict | None = None) -> dict:
        out = dict(empty)
        out["transcript_quality"] = {**(quality or {}), "status": status}
        return out

    wav = extract_audio(video_path)
    if wav is None:
        return unavailable("no_audio_track")

    try:
        model = _get_model()
        raw_segments, info = model.transcribe(
            str(wav),
            language="ko",
            vad_filter=True,
            vad_parameters={"min_silence_duration_ms": 500},
            word_timestamps=True,
            beam_size=1,
            # 앞 구간의 텍스트를 다음 구간 디코딩에 넣지 않는다. 한 번 지어낸 문장이
            # 뒤로 계속 번지는 반복 환각을 막는 가장 효과적인 설정이다.
            condition_on_previous_text=False,
        )

        segments: list[dict] = []
        for seg in raw_segments:
            segments.append({
                "start": seg.start,
                "end": seg.end,
                "text": seg.text.strip(),
                # 필러워드 타임스탬프를 만들려면 단어별 시각이 필요하다.
                "words": [{"text": w.word, "start": w.start} for w in (seg.words or [])],
                "no_speech_prob": getattr(seg, "no_speech_prob", None),
                "avg_logprob": getattr(seg, "avg_logprob", None),
            })

        raw_count = len(segments)
        duration = float(getattr(info, "duration", 0.0)) or (segments[-1]["end"] if segments else 0.0)

        segments, dropped = _filter_hallucinations(segments)
        quality = {
            "raw_segments": raw_count,
            "kept_segments": len(segments),
            "dropped": dropped,
        }
        problem = _speech_plausibility(segments, duration)
        if problem:
            logger.info("음성 분석 불가 (%s): %s", problem, quality)
            return unavailable(problem, quality)
        quality["status"] = "ok"
        transcript = " ".join(seg["text"] for seg in segments).strip()

        speech_sec = sum(seg["end"] - seg["start"] for seg in segments)
        syllables = _count_syllables(transcript)
        speech_rate = (syllables / speech_sec * 60) if speech_sec > 0 else 0.0

        filler_count, filler_detail, filler_words = _count_fillers(segments)
        filler_per_min = (filler_count / duration * 60) if duration > 0 else 0.0

        silence_ratio, long_count, long_gaps = _silence_stats(segments, duration)

        frames = _pitch_frames(wav)
        if frames is None:
            pitch_cv = pitch_median = pitch_std = 0.0
            timeline = []
        else:
            f0, rms = frames
            pitch_cv, pitch_median, pitch_std = _pitch_variation(f0, rms)
            timeline = _build_timeline(f0, rms, segments, duration)
        monotone = _monotone_ratio(timeline)

        return {
            "speech_available": True,
            "speech_rate_spm": round(speech_rate, 1),
            "filler_count": filler_count,
            "filler_per_min": round(filler_per_min, 2),
            "filler_detail": filler_detail,
            "filler_words": filler_words,
            "timeline": timeline,
            "audio_silence_ratio": round(silence_ratio, 3),
            "long_silence_count": long_count,
            "long_silences": long_gaps,
            "pitch_cv": round(pitch_cv, 3),
            "pitch_median_hz": round(pitch_median, 1),
            "pitch_std_hz": round(pitch_std, 1),
            "monotone_ratio": monotone,
            "transcript": transcript[:5000],
            # 공유 스키마의 audio.transcript[]로 나가는 원본. 문장 병합 없이 Whisper 세그먼트 그대로 둔다.
            "segments": [
                {"start": round(s["start"], 1), "end": round(s["end"], 1), "text": s["text"]}
                for s in segments
            ],
            "speech_duration_sec": round(speech_sec, 1),
            "duration_sec": round(duration, 1),
            "transcript_quality": quality,
        }
    except Exception as exc:
        logger.warning("음성 분석 실패: %s", exc)
        return unavailable("transcription_error")
    finally:
        wav.unlink(missing_ok=True)

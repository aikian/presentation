"""Whisper 환각 필터 동작 확인.

조용한 구간에서 지어낸 아웃트로 문구, 같은 문장 반복, 한 단어만 늘어놓은 세그먼트를
버리고, 걸러낸 뒤 발화가 너무 적으면 음성 분석 불가로 판정하는지 본다.
"""
import unittest

from app.services.audio_analyzer import _filter_hallucinations, _speech_plausibility


def _seg(text, start=0.0, end=2.0, **extra):
    return {"start": start, "end": end, "text": text, "words": [], **extra}


class HallucinationFilterTests(unittest.TestCase):
    def test_normal_speech_is_kept(self):
        segs = [_seg("오늘 발표 주제는 인공지능입니다.", 0, 3), _seg("먼저 배경을 설명드리겠습니다.", 3, 6)]
        kept, dropped = _filter_hallucinations(segs)
        self.assertEqual(len(kept), 2)
        self.assertEqual(sum(dropped.values()), 0)

    def test_outro_phrase_is_dropped(self):
        segs = [_seg("오늘 발표를 시작하겠습니다.", 0, 2), _seg("시청해 주셔서 감사합니다.", 10, 12)]
        kept, dropped = _filter_hallucinations(segs)
        self.assertEqual([s["text"] for s in kept], ["오늘 발표를 시작하겠습니다."])
        self.assertEqual(dropped["outro_phrase"], 1)

    def test_plain_thanks_at_end_is_not_dropped(self):
        # 발표 끝의 "감사합니다"는 정상 발화라 남겨야 한다.
        kept, dropped = _filter_hallucinations([_seg("이상으로 발표를 마치겠습니다. 감사합니다.")])
        self.assertEqual(len(kept), 1)
        self.assertEqual(dropped["outro_phrase"], 0)

    def test_repeated_segments_keep_first_two_only(self):
        segs = [_seg("네 그렇습니다.", i * 2, i * 2 + 2) for i in range(5)]
        kept, dropped = _filter_hallucinations(segs)
        self.assertEqual(len(kept), 2)
        self.assertEqual(dropped["repeated_segment"], 3)

    def test_repeated_word_segment_is_dropped(self):
        kept, dropped = _filter_hallucinations([_seg("네 네 네 네 네 네 네 네 네")])
        self.assertEqual(kept, [])
        self.assertEqual(dropped["repeated_word"], 1)

    def test_no_hangul_segment_is_dropped(self):
        kept, dropped = _filter_hallucinations([_seg("..."), _seg("Thank you for watching")])
        self.assertEqual(kept, [])
        self.assertEqual(dropped["no_hangul"], 2)

    def test_low_confidence_needs_both_signals(self):
        only_no_speech = _seg("발표를 이어가겠습니다.", no_speech_prob=0.95, avg_logprob=-0.3)
        both = _seg("발표를 이어가겠습니다.", start=5, end=7, no_speech_prob=0.95, avg_logprob=-1.5)
        kept, dropped = _filter_hallucinations([only_no_speech, both])
        self.assertEqual(len(kept), 1)
        self.assertEqual(dropped["low_confidence"], 1)


class SpeechPlausibilityTests(unittest.TestCase):
    def test_ok_when_enough_speech(self):
        segs = [_seg("오늘 발표 주제는 인공지능입니다.", 0, 3)]
        self.assertIsNone(_speech_plausibility(segs, duration=10.0))

    def test_empty_after_filter(self):
        self.assertEqual(_speech_plausibility([], duration=60.0), "no_speech_after_filter")

    def test_too_little_speech(self):
        segs = [_seg("안녕하세요.", 0, 1)]
        self.assertEqual(_speech_plausibility(segs, duration=600.0), "too_little_speech")

    def test_implausible_rate(self):
        # 1초에 30음절은 사람이 낼 수 없는 속도다.
        segs = [_seg("가" * 30, 0, 1)]
        self.assertEqual(_speech_plausibility(segs, duration=2.0), "implausible_rate")

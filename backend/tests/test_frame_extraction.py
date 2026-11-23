"""프레임 추출 한 번에 여러 간격을 뽑는 로직과 축소 함수 확인.

합성 영상(10fps, 5초)을 만들어 2초 간격과 0.5초 간격 프레임이 예전 방식과 같은
시각에 뽑히는지, 축소가 비율을 유지하는지 본다.
"""
import tempfile
import unittest
from pathlib import Path

import cv2
import numpy as np

from app.core.config import settings
from app.services.video_analyzer import _extract_frame_sets, _extract_frames, _shrink_frame


def _make_video(path: Path, seconds=5, fps=10, size=(320, 240)):
    writer = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"mp4v"), fps, size)
    for i in range(seconds * fps):
        frame = np.full((size[1], size[0], 3), i % 255, dtype=np.uint8)
        writer.write(frame)
    writer.release()


class ShrinkFrameTests(unittest.TestCase):
    def test_keeps_aspect_ratio_and_long_side(self):
        frame = np.zeros((1920, 1080, 3), dtype=np.uint8)
        out = _shrink_frame(frame, 640)
        self.assertEqual(out.shape[0], 640)
        self.assertEqual(out.shape[1], 360)

    def test_zero_means_no_change(self):
        frame = np.zeros((720, 1280, 3), dtype=np.uint8)
        self.assertIs(_shrink_frame(frame, 0), frame)

    def test_small_frame_is_not_upscaled(self):
        frame = np.zeros((240, 320, 3), dtype=np.uint8)
        self.assertIs(_shrink_frame(frame, 640), frame)


class FrameSetTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.video = Path(self.tmp.name) / "sample.mp4"
        _make_video(self.video)
        self.prev_side = settings.max_frame_side
        settings.max_frame_side = 0

    def tearDown(self):
        settings.max_frame_side = self.prev_side
        self.tmp.cleanup()

    def test_single_pass_matches_separate_passes(self):
        sets, last_sec = _extract_frame_sets(self.video, [2.0, 0.5])
        frames2, times2 = _extract_frames(self.video, 2.0)
        frames05, times05 = _extract_frames(self.video, 0.5)

        self.assertEqual(sets[2.0][1], times2)
        self.assertEqual(sets[0.5][1], times05)
        self.assertEqual(len(sets[2.0][0]), 3)     # 0, 2, 4초
        self.assertEqual(len(sets[0.5][0]), 10)    # 0, 0.5, ..., 4.5초
        self.assertAlmostEqual(last_sec, 4.9, places=2)

    def test_two_second_samples_are_subset_of_half_second_samples(self):
        sets, _ = _extract_frame_sets(self.video, [2.0, 0.5])
        self.assertTrue(set(sets[2.0][1]).issubset(set(sets[0.5][1])))

    def test_shrink_applies_to_extracted_frames(self):
        settings.max_frame_side = 160
        sets, _ = _extract_frame_sets(self.video, [2.0])
        h, w = sets[2.0][0][0].shape[:2]
        self.assertEqual((w, h), (160, 120))

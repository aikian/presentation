import unittest

from app.services.audio_analyzer import _count_fillers
from app.services.video_analyzer import (
    GAZE_AWAY_SCORE_THRESHOLD,
    GAZE_GRID_THRESHOLD,
    _gaze_grid_cell,
    _relative_gaze_score,
)


def _segments(*words):
    return [
        {
            "words": [
                {"text": word, "start": index * 0.5, "end": index * 0.5 + 0.3}
                for index, word in enumerate(words)
            ]
        }
    ]


class AudioMetricTests(unittest.TestCase):
    def test_demonstrative_geu_is_not_counted_as_filler(self):
        count, detail, occurrences = _count_fillers(_segments("그", "이유는", "명확합니다"))
        self.assertEqual(count, 0)
        self.assertEqual(detail, {})
        self.assertEqual(occurrences, [])

    def test_unambiguous_fillers_are_still_counted(self):
        count, detail, _ = _count_fillers(_segments("어", "그러니까", "음"))
        self.assertEqual(count, 3)
        self.assertEqual(detail, {"어": 1, "그러니까": 1, "음": 1})


class GazeMetricTests(unittest.TestCase):
    def test_center_cell_and_away_score_share_boundary(self):
        inside = GAZE_GRID_THRESHOLD - 0.001
        outside = GAZE_GRID_THRESHOLD + 0.001

        self.assertEqual(_gaze_grid_cell(inside, 0), (1, 1))
        self.assertLess(_relative_gaze_score(inside, 0), GAZE_AWAY_SCORE_THRESHOLD)
        self.assertEqual(_gaze_grid_cell(outside, 0), (1, 2))
        self.assertGreater(_relative_gaze_score(outside, 0), GAZE_AWAY_SCORE_THRESHOLD)


if __name__ == "__main__":
    unittest.main()

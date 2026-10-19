import unittest
from unittest.mock import patch

import httpx

from app.core.database import execute_supabase


class ExecuteSupabaseTests(unittest.TestCase):
    @patch("app.core.database.time.sleep")
    def test_retries_transient_transport_failure(self, sleep):
        responses = iter(
            [
                httpx.RemoteProtocolError("disconnected"),
                httpx.RemoteProtocolError("disconnected"),
                "saved",
            ]
        )
        calls = 0

        def operation():
            nonlocal calls
            calls += 1
            response = next(responses)
            if isinstance(response, Exception):
                raise response
            return response

        self.assertEqual(execute_supabase(operation), "saved")
        self.assertEqual(calls, 3)
        self.assertEqual([call.args[0] for call in sleep.call_args_list], [0.4, 0.8])

    @patch("app.core.database.time.sleep")
    def test_does_not_retry_non_transport_failure(self, sleep):
        calls = 0

        def operation():
            nonlocal calls
            calls += 1
            raise ValueError("invalid payload")

        with self.assertRaises(ValueError):
            execute_supabase(operation)
        self.assertEqual(calls, 1)
        sleep.assert_not_called()

    @patch("app.core.database.time.sleep")
    def test_raises_after_retry_budget(self, sleep):
        calls = 0

        def operation():
            nonlocal calls
            calls += 1
            raise httpx.ReadTimeout("timeout")

        with self.assertRaises(httpx.ReadTimeout):
            execute_supabase(operation, attempts=2)
        self.assertEqual(calls, 2)
        self.assertEqual(sleep.call_count, 1)


if __name__ == "__main__":
    unittest.main()

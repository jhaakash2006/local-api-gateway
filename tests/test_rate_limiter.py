import concurrent.futures
import unittest

from rate_limiter.fixed_window import FixedWindowRateLimiter
from rate_limiter.sliding_window import SlidingWindowRateLimiter


class TestRateLimiters(unittest.TestCase):

    def test_fixed_window_limit(self):
        limiter = FixedWindowRateLimiter(
            limit=2,
            window_seconds=5
        )

        self.assertTrue(limiter.is_allowed("client-1"))
        self.assertTrue(limiter.is_allowed("client-1"))
        self.assertFalse(limiter.is_allowed("client-1"))

    def test_sliding_window_limit(self):
        limiter = SlidingWindowRateLimiter(
            limit=2,
            window_seconds=5
        )

        self.assertTrue(limiter.is_allowed("client-1"))
        self.assertTrue(limiter.is_allowed("client-1"))
        self.assertFalse(limiter.is_allowed("client-1"))

    def test_clients_are_isolated(self):
        limiter = SlidingWindowRateLimiter(
            limit=2,
            window_seconds=5
        )

        self.assertTrue(limiter.is_allowed("client-1"))
        self.assertTrue(limiter.is_allowed("client-1"))
        self.assertFalse(limiter.is_allowed("client-1"))

        self.assertTrue(limiter.is_allowed("client-2"))
        self.assertTrue(limiter.is_allowed("client-2"))
        self.assertFalse(limiter.is_allowed("client-2"))

    def test_concurrent_requests_are_limited(self):
        limiter = SlidingWindowRateLimiter(
            limit=2,
            window_seconds=5
        )

        def send_request():
            return limiter.is_allowed("client-1")

        with concurrent.futures.ThreadPoolExecutor(
            max_workers=10
        ) as executor:

            results = list(
                executor.map(
                    lambda _: send_request(),
                    range(10)
                )
            )

        self.assertEqual(results.count(True), 2)
        self.assertEqual(results.count(False), 8)


if __name__ == "__main__":
    unittest.main()
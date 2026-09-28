import time
import threading


class FixedWindowRateLimiter:
    def __init__(self, limit=5, window_seconds=60):
        self.limit = limit
        self.window_seconds = window_seconds
        self.window_start = None
        self.count = 0
        self.lock = threading.Lock()

    def is_allowed(self, client_id=None):
        current_time = time.time()
        window_start = (
            current_time
            - (current_time % self.window_seconds)
        )

        with self.lock:
            if self.window_start != window_start:
                self.window_start = window_start
                self.count = 0

            if self.count >= self.limit:
                return False

            self.count += 1
            return True
import time
import threading


class SlidingWindowRateLimiter:

    def __init__(self, limit=5, window_seconds=60):
        self.limit = limit
        self.window_seconds = window_seconds
        self.requests = []
        self.lock = threading.Lock()

    def is_allowed(self, client_id):

        current_time = time.time()

        with self.lock:

            window_start = current_time - self.window_seconds

            self.requests[:] = [
                request_time
                for request_time in self.requests
                if request_time > window_start
            ]

            if len(self.requests) >= self.limit:
                return False

            self.requests.append(current_time)

            return True
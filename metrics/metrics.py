import threading
import time


class MetricsCollector:

    def __init__(self):

        self.lock = threading.Lock()

        self.total_requests = 0
        self.allowed_requests = 0
        self.blocked_requests = 0

        self.backend_errors = 0
        self.backend_timeouts = 0

        self.request_logs = []

    def record_request(
        self,
        endpoint,
        client_ip,
        status_code,
        response_time,
        rate_limited=False,
        backend_error=False,
        backend_timeout=False
    ):

        with self.lock:

            self.total_requests += 1

            if rate_limited:

                self.blocked_requests += 1

            else:

                self.allowed_requests += 1

            if backend_error:

                self.backend_errors += 1

            if backend_timeout:

                self.backend_timeouts += 1

            self.request_logs.append({
                "endpoint": endpoint,
                "client_ip": client_ip,
                "timestamp": time.time(),
                "status_code": status_code,
                "response_time": response_time
            })

    def get_metrics(self):

        with self.lock:

            return {
                "total_requests": self.total_requests,
                "allowed_requests": self.allowed_requests,
                "blocked_requests": self.blocked_requests,
                "backend_errors": self.backend_errors,
                "backend_timeouts": self.backend_timeouts,
                "requests": list(self.request_logs)
            }

    def reset_metrics(self):

        with self.lock:

            self.total_requests = 0
            self.allowed_requests = 0
            self.blocked_requests = 0

            self.backend_errors = 0
            self.backend_timeouts = 0

            self.request_logs.clear()
import unittest

from metrics.metrics import MetricsCollector


class MetricsCollectorTest(unittest.TestCase):

    def setUp(self):

        self.metrics = MetricsCollector()

    def test_total_and_allowed_requests(self):

        self.metrics.record_request(
            endpoint="/api/users/users",
            client_ip="127.0.0.1",
            status_code=200,
            response_time=0.05
        )

        result = self.metrics.get_metrics()

        self.assertEqual(result["total_requests"], 1)
        self.assertEqual(result["allowed_requests"], 1)
        self.assertEqual(result["blocked_requests"], 0)

    def test_blocked_requests(self):

        self.metrics.record_request(
            endpoint="/api/users/users",
            client_ip="127.0.0.1",
            status_code=429,
            response_time=0.01,
            rate_limited=True
        )

        result = self.metrics.get_metrics()

        self.assertEqual(result["total_requests"], 1)
        self.assertEqual(result["allowed_requests"], 0)
        self.assertEqual(result["blocked_requests"], 1)

    def test_backend_errors_and_timeouts(self):

        self.metrics.record_request(
            endpoint="/api/orders/orders",
            client_ip="127.0.0.1",
            status_code=503,
            response_time=0.10,
            backend_error=True
        )

        self.metrics.record_request(
            endpoint="/api/orders/slow-orders",
            client_ip="127.0.0.1",
            status_code=504,
            response_time=2.00,
            backend_timeout=True
        )

        result = self.metrics.get_metrics()

        self.assertEqual(result["total_requests"], 2)
        self.assertEqual(result["allowed_requests"], 2)
        self.assertEqual(result["blocked_requests"], 0)
        self.assertEqual(result["backend_errors"], 1)
        self.assertEqual(result["backend_timeouts"], 1)

    def test_request_log_details(self):

        self.metrics.record_request(
            endpoint="/api/products/products",
            client_ip="127.0.0.1",
            status_code=200,
            response_time=0.25
        )

        result = self.metrics.get_metrics()

        self.assertEqual(len(result["requests"]), 1)

        log = result["requests"][0]

        self.assertEqual(log["endpoint"], "/api/products/products")
        self.assertEqual(log["client_ip"], "127.0.0.1")
        self.assertEqual(log["status_code"], 200)
        self.assertEqual(log["response_time"], 0.25)
        self.assertIn("timestamp", log)

    def test_reset_metrics(self):

        self.metrics.record_request(
            endpoint="/api/users/users",
            client_ip="127.0.0.1",
            status_code=200,
            response_time=0.05
        )

        self.metrics.reset_metrics()

        result = self.metrics.get_metrics()

        self.assertEqual(result["total_requests"], 0)
        self.assertEqual(result["allowed_requests"], 0)
        self.assertEqual(result["blocked_requests"], 0)
        self.assertEqual(result["backend_errors"], 0)
        self.assertEqual(result["backend_timeouts"], 0)
        self.assertEqual(result["requests"], [])


if __name__ == "__main__":
    unittest.main()
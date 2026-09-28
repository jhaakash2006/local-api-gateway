import unittest
from unittest.mock import patch
import requests

from gateway.app import app


class TestBackendTimeout(unittest.TestCase):

    def setUp(self):
        app.config["TESTING"] = True
        self.client = app.test_client()

        from gateway.app import sliding_window_limiter

        with sliding_window_limiter.lock:
            sliding_window_limiter.requests.clear()

    @patch("gateway.app.requests.request")
    def test_backend_read_timeout_returns_504(self, mock_request):

        mock_request.side_effect = requests.exceptions.ReadTimeout()

        response = self.client.get(
            "/api/orders/slow-orders"
        )

        self.assertEqual(
            response.status_code,
            504
        )

        data = response.get_json()

        self.assertEqual(
            data["error"],
            "Backend service timeout"
        )


if __name__ == "__main__":
    unittest.main()
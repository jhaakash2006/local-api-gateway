import unittest
from unittest.mock import patch
import requests

from gateway.app import app


class TestBackendFailures(unittest.TestCase):

    def setUp(self):
        app.config["TESTING"] = True
        self.client = app.test_client()

        from gateway.app import sliding_window_limiter

        with sliding_window_limiter.lock:
            sliding_window_limiter.requests.clear()

    @patch("gateway.app.requests.request")
    def test_backend_connection_failure_returns_503(self, mock_request):

        mock_request.side_effect = requests.exceptions.ConnectionError()

        response = self.client.get(
            "/api/orders/orders"
        )

        self.assertEqual(
            response.status_code,
            503
        )

        data = response.get_json()

        self.assertEqual(
            data["error"],
            "Backend service unavailable"
        )

    @patch("gateway.app.requests.request")
    def test_backend_4xx_returns_consistent_json_error(self, mock_request):

        backend_response = type(
            "BackendResponse",
            (),
            {
                "status_code": 404,
                "headers": {},
                "content": b"Not found"
            }
        )()

        mock_request.return_value = backend_response

        response = self.client.get(
            "/api/orders/unknown"
        )

        self.assertEqual(
            response.status_code,
            404
        )

        data = response.get_json()

        self.assertEqual(
            data["error"],
            "Backend returned an error"
        )

        self.assertEqual(
            data["status_code"],
            404
        )


if __name__ == "__main__":
    unittest.main()
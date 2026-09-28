import unittest
from unittest.mock import Mock, patch

from gateway.app import app


class TestGatewayRouting(unittest.TestCase):

    def setUp(self):
     app.config["TESTING"] = True
     self.client = app.test_client()

     from gateway.app import sliding_window_limiter

     with sliding_window_limiter.lock:
        sliding_window_limiter.requests.clear()

    def create_backend_response(self, service_name):
        response = Mock()
        response.status_code = 200
        response.content = (
            f'{{"service":"{service_name}","message":"{service_name} service is working"}}'
        ).encode()

        response.headers = {
            "Content-Type": "application/json"
        }

        return response

    @patch("gateway.app.requests.request")
    def test_users_route(self, mock_request):
        mock_request.return_value = self.create_backend_response("user")

        response = self.client.get(
            "/api/users/users"
        )

        self.assertEqual(response.status_code, 200)

        mock_request.assert_called_once()

        call_arguments = mock_request.call_args.kwargs

        self.assertEqual(
            call_arguments["url"],
            "http://127.0.0.1:5001/users"
        )

    @patch("gateway.app.requests.request")
    def test_orders_route(self, mock_request):
        mock_request.return_value = self.create_backend_response("order")

        response = self.client.get(
            "/api/orders/orders"
        )

        self.assertEqual(response.status_code, 200)

        call_arguments = mock_request.call_args.kwargs

        self.assertEqual(
            call_arguments["url"],
            "http://127.0.0.1:5002/orders"
        )

    @patch("gateway.app.requests.request")
    def test_products_route(self, mock_request):
        mock_request.return_value = self.create_backend_response("product")

        response = self.client.get(
            "/api/products/products"
        )

        self.assertEqual(response.status_code, 200)

        call_arguments = mock_request.call_args.kwargs

        self.assertEqual(
            call_arguments["url"],
            "http://127.0.0.1:5003/products"
        )

    def test_unknown_service(self):
        response = self.client.get(
            "/api/payment/payments"
        )

        self.assertEqual(response.status_code, 404)

        data = response.get_json()

        self.assertEqual(
            data["error"],
            "Unknown service"
        )


if __name__ == "__main__":
    unittest.main()
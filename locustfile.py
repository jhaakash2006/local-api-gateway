from locust import HttpUser, task, between, events
import time
import logging
import threading

from database.database import (
    start_test_run,
    finish_test_run,
    record_test_result
)

logger = logging.getLogger(__name__)

current_test_run_id = None
test_started_at = None

client_counter = 0
client_counter_lock = threading.Lock()


@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    global current_test_run_id
    global test_started_at

    test_started_at = time.time()

    current_test_run_id = start_test_run(
        test_name="Locust Load Test",
        description="Locust traffic through simulated public HTTPS endpoint"
    )

    logger.info(
        "Locust test started. Test run ID: %s",
        current_test_run_id
    )


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    global current_test_run_id
    global test_started_at

    if current_test_run_id is None:
        return

    try:
        duration = time.time() - test_started_at

        if duration <= 0:
            duration = 0.001

        total_stats = environment.stats.total

        total_requests = total_stats.num_requests
        total_failures = total_stats.num_failures

        total_failure_rate = 0.0

        if total_requests > 0:
            total_failure_rate = (
                total_failures / total_requests
            ) * 100

        total_rps = total_requests / duration

        record_test_result(
            test_run_id=current_test_run_id,
            endpoint="TOTAL",
            method="ALL",
            request_count=total_requests,
            failure_count=total_failures,
            failure_rate=total_failure_rate,
            requests_per_second=total_rps,
            average_response_time=total_stats.avg_response_time,
            min_response_time=total_stats.min_response_time,
            max_response_time=total_stats.max_response_time
        )

        for entry in environment.stats.entries.values():
            request_count = entry.num_requests
            failure_count = entry.num_failures

            failure_rate = 0.0

            if request_count > 0:
                failure_rate = (
                    failure_count / request_count
                ) * 100

            requests_per_second = request_count / duration

            record_test_result(
                test_run_id=current_test_run_id,
                endpoint=entry.name,
                method=entry.method,
                request_count=request_count,
                failure_count=failure_count,
                failure_rate=failure_rate,
                requests_per_second=requests_per_second,
                average_response_time=entry.avg_response_time,
                min_response_time=entry.min_response_time,
                max_response_time=entry.max_response_time
            )

        status = "FAILED" if total_failures > 0 else "COMPLETED"

        finish_test_run(
            test_run_id=current_test_run_id,
            status=status
        )

        logger.info(
            "Locust test finished. Test run ID: %s",
            current_test_run_id
        )

    except Exception as error:
        logger.error(
            "Failed to save Locust test results: %s",
            error
        )

        try:
            finish_test_run(
                test_run_id=current_test_run_id,
                status="FAILED"
            )
        except Exception as finish_error:
            logger.error(
                "Failed to finish Locust test run: %s",
                finish_error
            )


class GatewayUser(HttpUser):
    wait_time = between(1, 2)

    def on_start(self):
        global client_counter

        self.client.verify = False

        with client_counter_lock:
            client_counter += 1
            client_number = client_counter

        ip_number = ((client_number - 1) % 200) + 1

        self.simulated_ip = f"10.10.0.{ip_number}"

    def gateway_headers(self):
        return {
            "X-Forwarded-For": self.simulated_ip
        }

    @task(3)
    def get_users(self):
        self.client.get(
            "/api/users/users",
            headers=self.gateway_headers(),
            name="GET /api/users/users"
        )

    @task(2)
    def get_orders(self):
        self.client.get(
            "/api/orders/orders",
            headers=self.gateway_headers(),
            name="GET /api/orders/orders"
        )

    @task(2)
    def get_products(self):
        self.client.get(
            "/api/products/products",
            headers=self.gateway_headers(),
            name="GET /api/products/products"
        )

    @task(1)
    def health_check(self):
        self.client.get(
            "/api/health",
            headers=self.gateway_headers(),
            name="GET /api/health"
        )

    @task(1)
    def create_user(self):
        self.client.post(
            "/api/users/users",
            json={
                "name": "Locust User",
                "email": "locust@example.com"
            },
            headers={
                "X-Test-Header": "Locust-Test",
                "X-Forwarded-For": self.simulated_ip
            },
            name="POST /api/users/users"
        )

    @task(1)
    def create_product(self):
        self.client.post(
            "/api/products/products",
            json={
                "name": "Locust Product",
                "price": 99.99
            },
            headers=self.gateway_headers(),
            name="POST /api/products/products"
        )

    @task(1)
    def create_order(self):
        self.client.post(
            "/api/orders/orders",
            json={
                "user_id": 1,
                "product_name": "Locust Product",
                "quantity": 1
            },
            headers=self.gateway_headers(),
            name="POST /api/orders/orders"
        )

    @task(1)
    def unknown_route(self):
        with self.client.get(
            "/api/unknown/route",
            headers=self.gateway_headers(),
            name="GET /api/unknown/route",
            catch_response=True
        ) as response:
            if response.status_code == 404:
                response.success()
            else:
                response.failure(
                    "Expected 404, received "
                    + str(response.status_code)
                )

    @task(1)
    def slow_backend_timeout(self):
        with self.client.get(
            "/api/orders/slow-orders",
            headers=self.gateway_headers(),
            name="GET /api/orders/slow-orders",
            catch_response=True
        ) as response:
            if response.status_code == 504:
                response.success()
            elif response.status_code == 200:
                response.failure(
                    "Slow backend did not timeout"
                )
            else:
                response.failure(
                    "Expected 504, received "
                    + str(response.status_code)
                )
import sys
import time
import logging
import threading
from pathlib import Path

from flask import Flask, request, jsonify
import requests

PROJECT_ROOT = Path(__file__).resolve().parent.parent

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config import (
    GATEWAY_HOST,
    GATEWAY_PORT,
    USER_SERVICE_URL,
    ORDER_SERVICE_URL,
    PRODUCT_SERVICE_URL,
    RATE_LIMIT,
    RATE_LIMIT_WINDOW,
    RATE_LIMIT_ALGORITHM,
    BACKEND_TIMEOUT,
    TRUSTED_PROXY_IPS
)

from rate_limiter.fixed_window import FixedWindowRateLimiter
from rate_limiter.sliding_window import SlidingWindowRateLimiter
from metrics.metrics import MetricsCollector

from database.database import (
    record_gateway_request,
    record_rate_limit_event,
    record_backend_event
)

app = Flask(__name__)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)

logger = logging.getLogger(__name__)

BACKEND_SERVICES = {
    "users": USER_SERVICE_URL,
    "orders": ORDER_SERVICE_URL,
    "products": PRODUCT_SERVICE_URL
}

fixed_window_limiter = FixedWindowRateLimiter(
    limit=RATE_LIMIT,
    window_seconds=RATE_LIMIT_WINDOW
)

sliding_window_limiter = SlidingWindowRateLimiter(
    limit=RATE_LIMIT,
    window_seconds=RATE_LIMIT_WINDOW
)

active_rate_limit = RATE_LIMIT
active_rate_limit_window = RATE_LIMIT_WINDOW
active_rate_limit_algorithm = RATE_LIMIT_ALGORITHM

rate_limit_config_lock = threading.Lock()

metrics = MetricsCollector()


def is_dashboard_request():
    if request.headers.get("X-Dashboard-Request") != "true":
        return False

    remote_ip = request.remote_addr or ""

    return remote_ip in TRUSTED_PROXY_IPS


def get_client_ip():
    remote_ip = request.remote_addr or "unknown"

    if remote_ip not in TRUSTED_PROXY_IPS:
        return remote_ip

    forwarded_for = request.headers.get("X-Forwarded-For")

    if not forwarded_for:
        return remote_ip

    client_ip = forwarded_for.split(",")[0].strip()

    return client_ip or remote_ip


def is_rate_limit_allowed(client_id):
    with rate_limit_config_lock:
        algorithm = active_rate_limit_algorithm

        limiter = (
            fixed_window_limiter
            if algorithm == "fixed"
            else sliding_window_limiter
        )

    return limiter.is_allowed(client_id)


def get_forward_headers():
    excluded_headers = {
        "host",
        "content-length",
        "connection",
        "keep-alive",
        "proxy-authenticate",
        "proxy-authorization",
        "te",
        "trailer",
        "transfer-encoding",
        "upgrade"
    }

    return {
        key: value
        for key, value in request.headers.items()
        if key.lower() not in excluded_headers
    }


def get_response_headers(response):
    excluded_headers = {
        "server",
        "date",
        "connection",
        "keep-alive",
        "transfer-encoding",
        "content-length"
    }

    return [
        (key, value)
        for key, value in response.headers.items()
        if key.lower() not in excluded_headers
    ]


def get_backend_service_name(endpoint):
    parts = endpoint.strip("/").split("/")

    if len(parts) >= 2:
        service_name = parts[1]

        if service_name == "users":
            return "user"

        if service_name == "orders":
            return "order"

        if service_name == "products":
            return "product"

    return "unknown"


def record_metrics(
    endpoint,
    method,
    client_ip,
    status_code,
    start_time,
    rate_limited=False,
    backend_error=False,
    backend_timeout=False,
    skip_database=False
):
    response_time = time.time() - start_time

    metrics.record_request(
        endpoint=endpoint,
        client_ip=client_ip,
        status_code=status_code,
        response_time=response_time,
        rate_limited=rate_limited,
        backend_error=backend_error,
        backend_timeout=backend_timeout
    )

    if not skip_database:
        try:
            record_gateway_request(
                method=method,
                endpoint=endpoint,
                client_ip=client_ip,
                status_code=status_code,
                response_time=response_time
            )

        except Exception as error:
            logger.error(
                "Database gateway request record failed | error=%s",
                error
            )

    return response_time


def record_rate_limit_result(
    client_ip,
    endpoint,
    allowed,
    skip_database=False
):
    if skip_database:
        return

    try:
        with rate_limit_config_lock:
            algorithm = active_rate_limit_algorithm
            limit_value = active_rate_limit
            window_seconds = active_rate_limit_window

        record_rate_limit_event(
            client_ip=client_ip,
            endpoint=endpoint,
            algorithm=algorithm,
            allowed=allowed,
            limit_value=limit_value,
            window_seconds=window_seconds
        )

    except Exception as error:
        logger.error(
            "Database rate limit record failed | error=%s",
            error
        )


def record_backend_result(
    endpoint,
    event_type,
    status_code,
    response_time,
    skip_database=False
):
    if skip_database:
        return

    try:
        service = get_backend_service_name(endpoint)

        details = f"response_time={response_time:.6f}"

        record_backend_event(
            service=service,
            endpoint=endpoint,
            event_type=event_type,
            status_code=status_code,
            details=details
        )

    except Exception as error:
        logger.error(
            "Database backend event record failed | error=%s",
            error
        )


@app.route("/api/health", methods=["GET"])
def health():
    logger.info("Health check received")

    return jsonify({
        "status": "healthy"
    }), 200


@app.route("/api/rate-limit", methods=["GET"])
def get_rate_limit():
    with rate_limit_config_lock:
        return jsonify({
            "limit": active_rate_limit,
            "window_seconds": active_rate_limit_window,
            "algorithm": active_rate_limit_algorithm
        }), 200


@app.route("/api/rate-limit", methods=["POST"])
def update_rate_limit():
    global active_rate_limit
    global active_rate_limit_window
    global active_rate_limit_algorithm

    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return jsonify({
            "error": "Request body must be a JSON object"
        }), 400

    limit = data.get("limit")
    window_seconds = data.get("window_seconds")
    algorithm = data.get("algorithm")

    if not isinstance(limit, int) or isinstance(limit, bool):
        return jsonify({
            "error": "limit must be an integer"
        }), 400

    if not isinstance(window_seconds, int) or isinstance(window_seconds, bool):
        return jsonify({
            "error": "window_seconds must be an integer"
        }), 400

    if algorithm not in ["fixed", "sliding"]:
        return jsonify({
            "error": "algorithm must be fixed or sliding"
        }), 400

    if limit < 1 or limit > 10000:
        return jsonify({
            "error": "limit must be between 1 and 10000"
        }), 400

    if window_seconds < 1 or window_seconds > 3600:
        return jsonify({
            "error": "window_seconds must be between 1 and 3600"
        }), 400

    with rate_limit_config_lock:
        active_rate_limit = limit
        active_rate_limit_window = window_seconds
        active_rate_limit_algorithm = algorithm

        fixed_window_limiter.limit = limit
        fixed_window_limiter.window_seconds = window_seconds

        sliding_window_limiter.limit = limit
        sliding_window_limiter.window_seconds = window_seconds

        with fixed_window_limiter.lock:
            fixed_window_limiter.window_start = None
            fixed_window_limiter.count = 0

        with sliding_window_limiter.lock:
            sliding_window_limiter.requests.clear()

    logger.info(
        "Rate limit configuration updated | limit=%s window=%s algorithm=%s",
        limit,
        window_seconds,
        algorithm
    )

    return jsonify({
        "message": "Rate limit configuration updated",
        "limit": limit,
        "window_seconds": window_seconds,
        "algorithm": algorithm
    }), 200


@app.route(
    "/api/<service>/<path:path>",
    methods=["GET", "POST", "PUT", "DELETE"]
)
def gateway(service, path):
    start_time = time.time()
    client_id = get_client_ip()
    endpoint = request.path
    method = request.method
    dashboard_request = is_dashboard_request()

    logger.info(
        "Request received | method=%s endpoint=%s client=%s dashboard=%s",
        method,
        endpoint,
        client_id,
        dashboard_request
    )

    if service not in BACKEND_SERVICES:
        response_time = record_metrics(
            endpoint=endpoint,
            method=method,
            client_ip=client_id,
            status_code=404,
            start_time=start_time,
            skip_database=dashboard_request
        )

        logger.warning(
            "Unknown service | service=%s endpoint=%s response_time=%.3fs",
            service,
            endpoint,
            response_time
        )

        return jsonify({
            "error": "Unknown service"
        }), 404

    if dashboard_request:
        allowed = True
    else:
        allowed = is_rate_limit_allowed(client_id)

    record_rate_limit_result(
        client_ip=client_id,
        endpoint=endpoint,
        allowed=allowed,
        skip_database=dashboard_request
    )

    if not allowed:
        response_time = record_metrics(
            endpoint=endpoint,
            method=method,
            client_ip=client_id,
            status_code=429,
            start_time=start_time,
            rate_limited=True,
            skip_database=dashboard_request
        )

        logger.warning(
            "Rate limit exceeded | endpoint=%s client=%s response_time=%.3fs",
            endpoint,
            client_id,
            response_time
        )

        return jsonify({
            "error": "Rate limit exceeded"
        }), 429

    backend_url = f"{BACKEND_SERVICES[service]}/{path}"

    if request.query_string:
        backend_url = (
            f"{backend_url}?"
            f"{request.query_string.decode('utf-8')}"
        )

    logger.info(
        "Forwarding request | backend=%s",
        backend_url
    )

    try:
        response = requests.request(
            method=method,
            url=backend_url,
            headers=get_forward_headers(),
            data=request.get_data(),
            timeout=BACKEND_TIMEOUT
        )

        response_time = record_metrics(
            endpoint=endpoint,
            method=method,
            client_ip=client_id,
            status_code=response.status_code,
            start_time=start_time,
            skip_database=dashboard_request
        )

        logger.info(
            "Backend response | endpoint=%s status=%s response_time=%.3fs",
            endpoint,
            response.status_code,
            response_time
        )

        if response.status_code >= 400:
            record_backend_result(
                endpoint=endpoint,
                event_type="backend_error",
                status_code=response.status_code,
                response_time=response_time,
                skip_database=dashboard_request
            )

            return jsonify({
                "error": "Backend returned an error",
                "status_code": response.status_code
            }), response.status_code

        record_backend_result(
            endpoint=endpoint,
            event_type="backend_success",
            status_code=response.status_code,
            response_time=response_time,
            skip_database=dashboard_request
        )

        return (
            response.content,
            response.status_code,
            get_response_headers(response)
        )

    except requests.exceptions.ConnectTimeout:
        response_time = record_metrics(
            endpoint=endpoint,
            method=method,
            client_ip=client_id,
            status_code=503,
            start_time=start_time,
            backend_error=True,
            skip_database=dashboard_request
        )

        record_backend_result(
            endpoint=endpoint,
            event_type="connection_timeout",
            status_code=503,
            response_time=response_time,
            skip_database=dashboard_request
        )

        logger.error(
            "Backend connection timeout | endpoint=%s backend=%s response_time=%.3fs",
            endpoint,
            backend_url,
            response_time
        )

        return jsonify({
            "error": "Backend service unavailable"
        }), 503

    except requests.exceptions.ReadTimeout:
        response_time = record_metrics(
            endpoint=endpoint,
            method=method,
            client_ip=client_id,
            status_code=504,
            start_time=start_time,
            backend_timeout=True,
            skip_database=dashboard_request
        )

        record_backend_result(
            endpoint=endpoint,
            event_type="response_timeout",
            status_code=504,
            response_time=response_time,
            skip_database=dashboard_request
        )

        logger.warning(
            "Backend response timeout | endpoint=%s backend=%s response_time=%.3fs",
            endpoint,
            backend_url,
            response_time
        )

        return jsonify({
            "error": "Backend service timeout"
        }), 504

    except requests.exceptions.ConnectionError:
        response_time = record_metrics(
            endpoint=endpoint,
            method=method,
            client_ip=client_id,
            status_code=503,
            start_time=start_time,
            backend_error=True,
            skip_database=dashboard_request
        )

        record_backend_result(
            endpoint=endpoint,
            event_type="backend_unavailable",
            status_code=503,
            response_time=response_time,
            skip_database=dashboard_request
        )

        logger.error(
            "Backend unavailable | endpoint=%s backend=%s",
            endpoint,
            backend_url
        )

        return jsonify({
            "error": "Backend service unavailable"
        }), 503

    except requests.exceptions.RequestException:
        response_time = record_metrics(
            endpoint=endpoint,
            method=method,
            client_ip=client_id,
            status_code=503,
            start_time=start_time,
            backend_error=True,
            skip_database=dashboard_request
        )

        record_backend_result(
            endpoint=endpoint,
            event_type="backend_request_failed",
            status_code=503,
            response_time=response_time,
            skip_database=dashboard_request
        )

        logger.error(
            "Backend request failed | endpoint=%s backend=%s",
            endpoint,
            backend_url
        )

        return jsonify({
            "error": "Backend service unavailable"
        }), 503


@app.route("/api/metrics", methods=["GET"])
def get_metrics():
    logger.info("Metrics request received")

    return jsonify(
        metrics.get_metrics()
    ), 200


@app.route("/api/metrics/reset", methods=["POST"])
def reset_metrics():
    metrics.reset_metrics()

    logger.info(
        "Metrics reset requested"
    )

    return jsonify({
        "message": "Metrics reset successfully"
    }), 200


@app.errorhandler(404)
def handle_not_found(error):
    return jsonify({
        "error": "Route not found"
    }), 404


@app.errorhandler(405)
def handle_method_not_allowed(error):
    return jsonify({
        "error": "Method not allowed"
    }), 405


if __name__ == "__main__":
    logger.info(
        "Starting API Gateway | host=%s port=%s",
        GATEWAY_HOST,
        GATEWAY_PORT
    )

    app.run(
        host=GATEWAY_HOST,
        port=GATEWAY_PORT
    )
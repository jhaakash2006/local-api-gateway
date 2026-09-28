from flask import Flask, request, Response
import requests

app = Flask(__name__)

GATEWAY_URL = "http://127.0.0.1:8000"

@app.route("/", defaults={"path": ""}, methods=["GET", "POST", "PUT", "DELETE"])
@app.route("/<path:path>", methods=["GET", "POST", "PUT", "DELETE"])
def proxy(path):
    target_url = f"{GATEWAY_URL}/{path}"

    if request.query_string:
        target_url = f"{target_url}?{request.query_string.decode('utf-8')}"

    headers = {
        key: value
        for key, value in request.headers.items()
        if key.lower() not in {
            "host",
            "content-length",
            "connection"
        }
    }

    headers["X-Forwarded-For"] = request.remote_addr or "unknown"
    headers["X-Forwarded-Proto"] = "https"
    headers["X-Proxy-Name"] = "simulated-python-proxy"

    try:
        response = requests.request(
            method=request.method,
            url=target_url,
            headers=headers,
            data=request.get_data(),
            timeout=5
        )

        response_headers = {
            key: value
            for key, value in response.headers.items()
            if key.lower() not in {
                "content-length",
                "connection",
                "transfer-encoding"
            }
        }

        return Response(
            response.content,
            status=response.status_code,
            headers=response_headers
        )

    except requests.exceptions.Timeout:
        return {
            "error": "Gateway proxy timeout"
        }, 504

    except requests.exceptions.ConnectionError:
        return {
            "error": "Gateway unavailable"
        }, 503

if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=8443,
        ssl_context=(
            "proxy/certs/gateway.local.crt",
            "proxy/certs/gateway.local.key"
        )
    )
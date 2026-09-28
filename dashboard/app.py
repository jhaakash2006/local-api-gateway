import sys
import time
from pathlib import Path

import requests
import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parent.parent

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from database.database import (
    get_database_summary,
    get_users,
    get_orders,
    get_products,
    get_gateway_requests,
    get_rate_limit_events,
    get_backend_events,
    get_test_runs,
    get_test_results,
    reset_database
)

GATEWAY_URL = "http://127.0.0.1:8000"
PUBLIC_URL = "https://gateway.local:8443"

SIMULATED_SERVER_IP = "10.10.76.11"
SIMULATED_DOMAIN = "gateway.local"
ENTRY_PORT = 8443

st.set_page_config(
    page_title="API Gateway Dashboard",
    page_icon="🌐",
    layout="wide"
)

st.markdown(
"""
<style>
.main {
    padding-top: 1rem;
}

.block-container {
    max-width: 1400px;
    padding-left: 2rem;
    padding-right: 2rem;
}

.deployment-card {
    padding: 20px;
    border-radius: 12px;
    background-color: #f5f9ff;
    border: 1px solid #d9e7f7;
    margin-bottom: 20px;
}

.flow-box {
    padding: 18px;
    border-radius: 10px;
    background-color: #f8fafc;
    border: 1px solid #dbe3ec;
    text-align: center;
    min-height: 90px;
    display: flex;
    align-items: center;
    justify-content: center;
}

.status-running {
    padding: 16px;
    border-radius: 10px;
    background-color: #eaf8ef;
    border: 1px solid #b8e2c4;
    color: #137333;
    font-weight: 600;
}

.status-stopped {
    padding: 16px;
    border-radius: 10px;
    background-color: #fdecec;
    border: 1px solid #f2b8b5;
    color: #b3261e;
    font-weight: 600;
}

.info-box {
    padding: 18px;
    border-radius: 10px;
    background-color: #eaf3ff;
    border: 1px solid #c9def7;
    color: #174a7c;
}
</style>
""",
unsafe_allow_html=True
)

st.title("API Gateway Dashboard")

st.caption(
"API Gateway monitoring, rate limiting, backend health and deployment simulation"
)

st.header("Request Flow")

flow1, arrow1, flow2, arrow2, flow3, arrow3, flow4 = st.columns(
[2, 0.5, 2, 0.5, 2, 0.5, 2]
)

with flow1:
    st.markdown(
"""
<div class="flow-box">
<b>Client / Locust</b>
</div>
""",
unsafe_allow_html=True
)

with arrow1:
    st.markdown(
"<br><h2>→</h2>",
unsafe_allow_html=True
)

with flow2:
    st.markdown(
"""
<div class="flow-box">
<b>HTTPS Reverse Proxy<br>:8443</b>
</div>
""",
unsafe_allow_html=True
)

with arrow2:
    st.markdown(
"<br><h2>→</h2>",
unsafe_allow_html=True
)

with flow3:
    st.markdown(
"""
<div class="flow-box">
<b>API Gateway<br>:8000</b>
</div>
""",
unsafe_allow_html=True
)

with arrow3:
    st.markdown(
"<br><h2>→</h2>",
unsafe_allow_html=True
)

with flow4:
    st.markdown(
"""
<div class="flow-box">
<b>Backend Services<br>:5001 / :5002 / :5003</b>
</div>
""",
unsafe_allow_html=True
)

st.header("Rate Limit Configuration")

current_rate_limit = None

try:
    rate_response = requests.get(
        f"{GATEWAY_URL}/api/rate-limit",
        timeout=2
    )

    if rate_response.status_code == 200:
        current_rate_limit = rate_response.json()

except requests.RequestException:
    current_rate_limit = None

if current_rate_limit:
    current_limit = current_rate_limit.get(
        "limit",
        5
    )
    current_window = current_rate_limit.get(
        "window_seconds",
        60
    )
    current_algorithm = current_rate_limit.get(
        "algorithm",
        "sliding"
    )
else:
    current_limit = 5
    current_window = 60
    current_algorithm = "sliding"

col1, col2, col3 = st.columns(3)

with col1:
    new_limit = st.number_input(
        "Requests allowed",
        min_value=1,
        max_value=10000,
        value=int(current_limit),
        step=1
    )

with col2:
    new_window = st.number_input(
        "Window seconds",
        min_value=1,
        max_value=3600,
        value=int(current_window),
        step=1
    )

with col3:
    new_algorithm = st.selectbox(
        "Algorithm",
        ["fixed", "sliding"],
        index=0 if current_algorithm == "fixed" else 1
    )

if st.button("Update Rate Limit"):
    try:
        update_response = requests.post(
            f"{GATEWAY_URL}/api/rate-limit",
            json={
                "limit": int(new_limit),
                "window_seconds": int(new_window),
                "algorithm": new_algorithm
            },
            timeout=2
        )

        if update_response.status_code == 200:
            st.success(
                "Rate limit configuration updated successfully."
            )
        else:
            st.error(
                f"Rate limit update failed: {update_response.text}"
            )

    except requests.RequestException as error:
        st.error(
            f"Gateway unavailable: {error}"
        )

st.divider()

st.header("Gateway Metrics")

metrics_data = None

try:
    metrics_response = requests.get(
        f"{GATEWAY_URL}/api/metrics",
        timeout=3
    )

    if metrics_response.status_code == 200:
        metrics_data = metrics_response.json()

except requests.RequestException:
    metrics_data = None

if metrics_data:
    total_requests = metrics_data.get(
        "total_requests",
        0
    )

    allowed_requests = metrics_data.get(
        "allowed_requests",
        0
    )

    blocked_requests = metrics_data.get(
        "blocked_requests",
        0
    )

    backend_errors = metrics_data.get(
        "backend_errors",
        0
    )

    backend_timeouts = metrics_data.get(
        "backend_timeouts",
        0
    )

    col1, col2, col3, col4, col5 = st.columns(5)

    with col1:
        st.metric(
            "Total Requests",
            total_requests
        )

    with col2:
        st.metric(
            "Allowed",
            allowed_requests
        )

    with col3:
        st.metric(
            "Rate Limited",
            blocked_requests
        )

    with col4:
        st.metric(
            "Backend Errors",
            backend_errors
        )

    with col5:
        st.metric(
            "Backend Timeouts",
            backend_timeouts
        )
else:
    st.warning(
        "Gateway metrics are currently unavailable."
    )

st.header("Reset Metrics")

if st.button("Reset Gateway Metrics"):
    try:
        reset_response = requests.post(
            f"{GATEWAY_URL}/api/metrics/reset",
            timeout=2
        )

        if reset_response.status_code == 200:
            st.success(
                "Gateway metrics reset successfully."
            )

            time.sleep(0.5)
            st.rerun()

        else:
            st.error(
                "Unable to reset gateway metrics."
            )

    except requests.RequestException as error:
        st.error(
            f"Gateway unavailable: {error}"
        )

st.header("Backend Health")

st.info(
"Backend health is shown from the persisted database events. "
"Refreshing the dashboard does not generate backend API requests."
)

backend_events = []

try:
    backend_events = get_backend_events()
except Exception:
    backend_events = []

backend_status = {
"User Service": "UNKNOWN",
"Order Service": "UNKNOWN",
"Product Service": "UNKNOWN"
}

for event in backend_events:
    service = event.get("service")

    if service == "user":
        backend_status["User Service"] = "AVAILABLE"

    elif service == "order":
        backend_status["Order Service"] = "AVAILABLE"

    elif service == "product":
        backend_status["Product Service"] = "AVAILABLE"

health_columns = st.columns(3)

for index, service_name in enumerate(
    backend_status
):
    with health_columns[index]:
        status = backend_status[service_name]

        if status == "AVAILABLE":
            st.markdown(
                f"""
                <div class="status-running">
                {service_name}: AVAILABLE
                </div>
                """,
                unsafe_allow_html=True
            )
        else:
            st.markdown(
                f"""
                <div class="info-box">
                {service_name}: STATUS FROM STORED EVENTS
                </div>
                """,
                unsafe_allow_html=True
            )

st.header("HTTP Status Summary")

if metrics_data:
    request_logs = metrics_data.get(
        "requests",
        []
    )

    if request_logs:
        status_counts = {}

        for log in request_logs:
            status_code = str(
                log.get(
                    "status_code",
                    "unknown"
                )
            )

            status_counts[status_code] = (
                status_counts.get(
                    status_code,
                    0
                ) + 1
            )

        status_rows = []

        for status_code, count in status_counts.items():
            status_rows.append(
                {
                    "Status Code": status_code,
                    "Requests": count
                }
            )

        status_rows.sort(
            key=lambda row: row["Status Code"]
        )

        st.dataframe(
            status_rows,
            use_container_width=True,
            hide_index=True
        )

    else:
        st.info(
            "No request data available yet."
        )
else:
    st.info(
        "HTTP status data is unavailable."
    )

st.header("Request Logs")

if metrics_data:
    request_logs = metrics_data.get(
        "requests",
        []
    )

    if request_logs:
        logs_rows = []

        for log in request_logs:
            row = dict(log)

            if "timestamp" in row:
                row["timestamp"] = time.strftime(
                    "%Y-%m-%d %H:%M:%S",
                    time.localtime(
                        row["timestamp"]
                    )
                )

            if "response_time" in row:
                row["response_time"] = round(
                    row["response_time"],
                    4
                )

            logs_rows.append(row)

        st.dataframe(
            logs_rows,
            use_container_width=True,
            hide_index=True
        )

    else:
        st.info(
            "No request logs available."
        )
else:
    st.info(
        "Request logs are unavailable."
    )

st.header("Dashboard Controls")

if st.button("Refresh Dashboard"):
    st.rerun()

st.caption(
    f"Deployment simulation endpoint: "
    f"https://{SIMULATED_DOMAIN}:{ENTRY_PORT}"
)

st.divider()

st.header("Database")


def make_serial_ids(rows):
    serial_rows = []

    for index, row in enumerate(rows, start=1):
        serial_row = dict(row)

        if "id" in serial_row:
            serial_row["id"] = index

        serial_rows.append(serial_row)

    return serial_rows


with st.expander(
    "Database Verification",
    expanded=False
):
    st.caption(
        "Central SQLite database containing project data and test records."
    )

    if st.button(
        "Refresh Database",
        key="refresh_database"
    ):
        st.rerun()

    try:
        database_summary = get_database_summary()

        st.subheader("Database Summary")

        summary_columns = st.columns(4)

        summary_items = [
            (
                "Users",
                database_summary.get(
                    "users",
                    0
                )
            ),
            (
                "Orders",
                database_summary.get(
                    "orders",
                    0
                )
            ),
            (
                "Products",
                database_summary.get(
                    "products",
                    0
                )
            ),
            (
                "Test Results",
                database_summary.get(
                    "test_results",
                    0
                )
            )
        ]

        for index, (label, value) in enumerate(
            summary_items
        ):
            with summary_columns[index]:
                st.metric(
                    label,
                    value
                )

        st.divider()

        stored_gateway_requests = get_gateway_requests()

        with st.expander(
            "Users",
            expanded=False
        ):
            users = get_users()

            if users:
                st.dataframe(
                    make_serial_ids(users),
                    use_container_width=True,
                    hide_index=True
                )
            else:
                st.info(
                    "No users stored in the database."
                )

            st.subheader("API Request Records")

            user_requests = []

            for row in stored_gateway_requests:
                endpoint = str(
                    row.get(
                        "endpoint",
                        ""
                    )
                )

                if (
                    endpoint == "/api/users"
                    or endpoint.startswith("/api/users/")
                ):
                    user_requests.append(row)

            if user_requests:
                st.dataframe(
                    make_serial_ids(user_requests),
                    use_container_width=True,
                    hide_index=True
                )
            else:
                st.info(
                    "No API request records found for the Users service."
                )

        with st.expander(
            "Orders",
            expanded=False
        ):
            orders = get_orders()

            if orders:
                st.dataframe(
                    make_serial_ids(orders),
                    use_container_width=True,
                    hide_index=True
                )
            else:
                st.info(
                    "No orders stored in the database."
                )

            st.subheader("API Request Records")

            order_requests = []

            for row in stored_gateway_requests:
                endpoint = str(
                    row.get(
                        "endpoint",
                        ""
                    )
                )

                if (
                    endpoint == "/api/orders"
                    or endpoint.startswith("/api/orders/")
                ):
                    order_requests.append(row)

            if order_requests:
                st.dataframe(
                    make_serial_ids(order_requests),
                    use_container_width=True,
                    hide_index=True
                )
            else:
                st.info(
                    "No API request records found for the Orders service."
                )

        with st.expander(
            "Products",
            expanded=False
        ):
            products = get_products()

            if products:
                st.dataframe(
                    make_serial_ids(products),
                    use_container_width=True,
                    hide_index=True
                )
            else:
                st.info(
                    "No products stored in the database."
                )

            st.subheader("API Request Records")

            product_requests = []

            for row in stored_gateway_requests:
                endpoint = str(
                    row.get(
                        "endpoint",
                        ""
                    )
                )

                if (
                    endpoint == "/api/products"
                    or endpoint.startswith("/api/products/")
                ):
                    product_requests.append(row)

            if product_requests:
                st.dataframe(
                    make_serial_ids(product_requests),
                    use_container_width=True,
                    hide_index=True
                )
            else:
                st.info(
                    "No API request records found for the Products service."
                )

        with st.expander(
            "Test Results",
            expanded=False
        ):
            test_results = get_test_results()

            if test_results:
                st.dataframe(
                    make_serial_ids(test_results),
                    use_container_width=True,
                    hide_index=True
                )
            else:
                st.info(
                    "No test results stored in the database."
                )

            st.subheader("HTTP Status Records")

            if stored_gateway_requests:
                st.dataframe(
                    make_serial_ids(stored_gateway_requests),
                    use_container_width=True,
                    hide_index=True
                )
            else:
                st.info(
                    "No HTTP request status records stored in the database."
                )

        st.divider()

        st.subheader("Database Reset")

        st.warning(
            "This will permanently clear the stored project data "
            "and test records from the central SQLite database."
        )

        if st.button(
            "Reset Database",
            key="reset_database"
        ):
            try:
                reset_database()

                st.success(
                    "Database reset successfully. "
                    "All stored records are now zero."
                )

                time.sleep(0.5)
                st.rerun()

            except Exception as error:
                st.error(
                    f"Database reset failed: {error}"
                )

    except Exception as error:
        st.error(
            f"Database is currently unavailable: {error}"
        )
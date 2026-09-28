import sqlite3
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATABASE_PATH = PROJECT_ROOT / "database" / "gateway.db"


def get_db_connection():
    connection = sqlite3.connect(
        DATABASE_PATH,
        timeout=30
    )

    connection.row_factory = sqlite3.Row

    connection.execute("PRAGMA journal_mode=WAL")
    connection.execute("PRAGMA foreign_keys=ON")
    connection.execute("PRAGMA busy_timeout=30000")

    return connection


def get_current_timestamp():
    return datetime.now(timezone.utc).isoformat()


def ensure_column(cursor, table_name, column_name, column_definition):
    cursor.execute(
        f"PRAGMA table_info({table_name})"
    )

    existing_columns = {
        row["name"]
        for row in cursor.fetchall()
    }

    if column_name not in existing_columns:
        cursor.execute(
            f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_definition}"
        )


def get_service_from_endpoint(endpoint):
    if not endpoint:
        return "unknown"

    parts = endpoint.strip("/").split("/")

    if len(parts) < 2:
        return "unknown"

    if parts[0] != "api":
        return "unknown"

    service_map = {
        "users": "user",
        "orders": "order",
        "products": "product"
    }

    return service_map.get(
        parts[1],
        parts[1]
    )


def initialize_database():
    DATABASE_PATH.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    connection = get_db_connection()

    try:
        cursor = connection.cursor()

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                product_name TEXT NOT NULL,
                quantity INTEGER NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                price REAL NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS gateway_requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                method TEXT NOT NULL,
                endpoint TEXT NOT NULL,
                client_ip TEXT,
                timestamp TEXT NOT NULL,
                status_code INTEGER,
                response_time REAL
            )
            """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS rate_limit_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                client_ip TEXT NOT NULL,
                endpoint TEXT,
                algorithm TEXT NOT NULL,
                allowed INTEGER NOT NULL,
                timestamp TEXT NOT NULL,
                limit_value INTEGER,
                window_seconds INTEGER
            )
            """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS backend_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                service TEXT NOT NULL,
                endpoint TEXT,
                event_type TEXT NOT NULL,
                status_code INTEGER,
                timestamp TEXT NOT NULL,
                details TEXT,
                client_ip TEXT,
                response_time REAL
            )
            """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS test_runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                test_name TEXT NOT NULL,
                description TEXT,
                started_at TEXT NOT NULL,
                finished_at TEXT,
                status TEXT NOT NULL
            )
            """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS test_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                test_run_id INTEGER NOT NULL,
                endpoint TEXT NOT NULL,
                method TEXT,
                request_count INTEGER NOT NULL,
                failure_count INTEGER NOT NULL,
                failure_rate REAL NOT NULL,
                requests_per_second REAL NOT NULL,
                average_response_time REAL,
                min_response_time REAL,
                max_response_time REAL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (test_run_id) REFERENCES test_runs(id)
            )
            """
        )

        ensure_column(
            cursor,
            "rate_limit_events",
            "limit_value",
            "INTEGER"
        )

        ensure_column(
            cursor,
            "rate_limit_events",
            "window_seconds",
            "INTEGER"
        )

        ensure_column(
            cursor,
            "backend_events",
            "client_ip",
            "TEXT"
        )

        ensure_column(
            cursor,
            "backend_events",
            "response_time",
            "REAL"
        )

        connection.commit()

    finally:
        connection.close()


def add_user(name, email):
    connection = get_db_connection()

    try:
        cursor = connection.cursor()

        cursor.execute(
            """
            INSERT INTO users (
                name,
                email,
                created_at
            )
            VALUES (?, ?, ?)
            """,
            (
                name,
                email,
                get_current_timestamp()
            )
        )

        connection.commit()

        return cursor.lastrowid

    finally:
        connection.close()


def get_users():
    connection = get_db_connection()

    try:
        cursor = connection.cursor()

        cursor.execute(
            """
            SELECT
                id,
                name,
                email,
                created_at
            FROM users
            ORDER BY id ASC
            """
        )

        return [
            dict(row)
            for row in cursor.fetchall()
        ]

    finally:
        connection.close()


def add_order(user_id, product_name, quantity):
    connection = get_db_connection()

    try:
        cursor = connection.cursor()

        cursor.execute(
            """
            INSERT INTO orders (
                user_id,
                product_name,
                quantity,
                created_at
            )
            VALUES (?, ?, ?, ?)
            """,
            (
                user_id,
                product_name,
                quantity,
                get_current_timestamp()
            )
        )

        connection.commit()

        return cursor.lastrowid

    finally:
        connection.close()


def get_orders():
    connection = get_db_connection()

    try:
        cursor = connection.cursor()

        cursor.execute(
            """
            SELECT
                id,
                user_id,
                product_name,
                quantity,
                created_at
            FROM orders
            ORDER BY id ASC
            """
        )

        return [
            dict(row)
            for row in cursor.fetchall()
        ]

    finally:
        connection.close()


def add_product(name, price):
    connection = get_db_connection()

    try:
        cursor = connection.cursor()

        cursor.execute(
            """
            INSERT INTO products (
                name,
                price,
                created_at
            )
            VALUES (?, ?, ?)
            """,
            (
                name,
                price,
                get_current_timestamp()
            )
        )

        connection.commit()

        return cursor.lastrowid

    finally:
        connection.close()


def get_products():
    connection = get_db_connection()

    try:
        cursor = connection.cursor()

        cursor.execute(
            """
            SELECT
                id,
                name,
                price,
                created_at
            FROM products
            ORDER BY id ASC
            """
        )

        return [
            dict(row)
            for row in cursor.fetchall()
        ]

    finally:
        connection.close()


def record_gateway_request(
    method,
    endpoint,
    client_ip,
    status_code,
    response_time
):
    connection = get_db_connection()

    try:
        cursor = connection.cursor()

        cursor.execute(
            """
            INSERT INTO gateway_requests (
                method,
                endpoint,
                client_ip,
                timestamp,
                status_code,
                response_time
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                method,
                endpoint,
                client_ip,
                get_current_timestamp(),
                status_code,
                response_time
            )
        )

        connection.commit()

    finally:
        connection.close()


def record_rate_limit_event(
    client_ip,
    endpoint,
    algorithm,
    allowed,
    limit_value=None,
    window_seconds=None
):
    connection = get_db_connection()

    try:
        cursor = connection.cursor()

        cursor.execute(
            """
            INSERT INTO rate_limit_events (
                client_ip,
                endpoint,
                algorithm,
                allowed,
                timestamp,
                limit_value,
                window_seconds
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                client_ip,
                endpoint,
                algorithm,
                1 if allowed else 0,
                get_current_timestamp(),
                limit_value,
                window_seconds
            )
        )

        connection.commit()

    finally:
        connection.close()


def record_backend_event(
    service=None,
    endpoint=None,
    event_type=None,
    status_code=None,
    details=None,
    client_ip=None,
    response_time=None
):
    connection = get_db_connection()

    try:
        cursor = connection.cursor()

        if not service:
            service = get_service_from_endpoint(endpoint)

        cursor.execute(
            """
            INSERT INTO backend_events (
                service,
                endpoint,
                event_type,
                status_code,
                timestamp,
                details,
                client_ip,
                response_time
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                service,
                endpoint,
                event_type,
                status_code,
                get_current_timestamp(),
                details,
                client_ip,
                response_time
            )
        )

        connection.commit()

    finally:
        connection.close()


def start_test_run(test_name, description=None):
    connection = get_db_connection()

    try:
        cursor = connection.cursor()

        cursor.execute(
            """
            INSERT INTO test_runs (
                test_name,
                description,
                started_at,
                status
            )
            VALUES (?, ?, ?, ?)
            """,
            (
                test_name,
                description,
                get_current_timestamp(),
                "RUNNING"
            )
        )

        connection.commit()

        return cursor.lastrowid

    finally:
        connection.close()


def finish_test_run(test_run_id, status):
    connection = get_db_connection()

    try:
        cursor = connection.cursor()

        cursor.execute(
            """
            UPDATE test_runs
            SET
                finished_at = ?,
                status = ?
            WHERE id = ?
            """,
            (
                get_current_timestamp(),
                status,
                test_run_id
            )
        )

        connection.commit()

    finally:
        connection.close()


def record_test_result(
    test_run_id,
    endpoint,
    method,
    request_count,
    failure_count,
    failure_rate,
    requests_per_second,
    average_response_time,
    min_response_time,
    max_response_time
):
    connection = get_db_connection()

    try:
        cursor = connection.cursor()

        cursor.execute(
            """
            INSERT INTO test_results (
                test_run_id,
                endpoint,
                method,
                request_count,
                failure_count,
                failure_rate,
                requests_per_second,
                average_response_time,
                min_response_time,
                max_response_time,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                test_run_id,
                endpoint,
                method,
                request_count,
                failure_count,
                failure_rate,
                requests_per_second,
                average_response_time,
                min_response_time,
                max_response_time,
                get_current_timestamp()
            )
        )

        connection.commit()

    finally:
        connection.close()


def get_gateway_requests():
    connection = get_db_connection()

    try:
        cursor = connection.cursor()

        cursor.execute(
            """
            SELECT
                id,
                method,
                endpoint,
                client_ip,
                timestamp,
                status_code,
                response_time
            FROM gateway_requests
            ORDER BY id DESC
            """
        )

        return [
            dict(row)
            for row in cursor.fetchall()
        ]

    finally:
        connection.close()


def get_rate_limit_events():
    connection = get_db_connection()

    try:
        cursor = connection.cursor()

        cursor.execute(
            """
            SELECT
                id,
                client_ip,
                endpoint,
                algorithm,
                limit_value,
                window_seconds,
                allowed,
                timestamp
            FROM rate_limit_events
            ORDER BY id DESC
            """
        )

        return [
            dict(row)
            for row in cursor.fetchall()
        ]

    finally:
        connection.close()


def get_backend_events():
    connection = get_db_connection()

    try:
        cursor = connection.cursor()

        cursor.execute(
            """
            SELECT
                id,
                service,
                endpoint,
                event_type,
                status_code,
                client_ip,
                response_time,
                timestamp,
                details
            FROM backend_events
            ORDER BY id DESC
            """
        )

        return [
            dict(row)
            for row in cursor.fetchall()
        ]

    finally:
        connection.close()


def get_test_runs():
    connection = get_db_connection()

    try:
        cursor = connection.cursor()

        cursor.execute(
            """
            SELECT
                id,
                test_name,
                description,
                started_at,
                finished_at,
                status
            FROM test_runs
            ORDER BY id DESC
            """
        )

        return [
            dict(row)
            for row in cursor.fetchall()
        ]

    finally:
        connection.close()


def get_test_results():
    connection = get_db_connection()

    try:
        cursor = connection.cursor()

        cursor.execute(
            """
            SELECT
                test_results.id,
                test_results.test_run_id,
                test_runs.test_name,
                test_results.endpoint,
                test_results.method,
                test_results.request_count,
                test_results.failure_count,
                test_results.failure_rate,
                test_results.requests_per_second,
                test_results.average_response_time,
                test_results.min_response_time,
                test_results.max_response_time,
                test_results.created_at
            FROM test_results
            INNER JOIN test_runs
                ON test_results.test_run_id = test_runs.id
            ORDER BY test_results.id DESC
            """
        )

        return [
            dict(row)
            for row in cursor.fetchall()
        ]

    finally:
        connection.close()


def get_database_summary():
    connection = get_db_connection()

    try:
        cursor = connection.cursor()

        tables = [
            "users",
            "orders",
            "products",
            "gateway_requests",
            "rate_limit_events",
            "backend_events",
            "test_runs",
            "test_results"
        ]

        summary = {}

        for table in tables:
            cursor.execute(
                f"SELECT COUNT(*) AS count FROM {table}"
            )

            row = cursor.fetchone()

            summary[table] = row["count"]

        return summary

    finally:
        connection.close()


def reset_database():
    connection = get_db_connection()

    try:
        cursor = connection.cursor()

        tables = [
            "test_results",
            "gateway_requests",
            "rate_limit_events",
            "backend_events",
            "test_runs",
            "orders",
            "products",
            "users"
        ]

        for table in tables:
            cursor.execute(
                f"DELETE FROM {table}"
            )

        for table in tables:
            cursor.execute(
                """
                DELETE FROM sqlite_sequence
                WHERE name = ?
                """,
                (table,)
            )

        connection.commit()

    finally:
        connection.close()


initialize_database()
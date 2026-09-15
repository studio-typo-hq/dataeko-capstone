import os
import time
from collections import defaultdict, deque

import psycopg
from flask import Flask, jsonify, request
from prometheus_client import (
    Counter,
    Gauge,
    Histogram,
    generate_latest,
    CONTENT_TYPE_LATEST,
)

app = Flask(__name__)

REQUESTS = Counter(
    "capstone_requests_total",
    "Total HTTP requests",
    ["endpoint", "method", "status"],
)

LATENCY = Histogram(
    "capstone_request_seconds",
    "Request latency in seconds",
    ["endpoint"],
)

IN_FLIGHT = Gauge(
    "capstone_orders_in_flight",
    "Number of HTTP requests currently in flight",
)

RATE_LIMIT = 10
RATE_WINDOW = 10
request_times = defaultdict(deque)


@app.before_request
def track_request_start():
    IN_FLIGHT.inc()


@app.after_request
def track_request_finish(response):
    IN_FLIGHT.dec()
    return response


def db():
    return psycopg.connect(os.environ.get("DB_DSN", "postgresql://aditya@localhost:5432/capstone"))


def authorised(req):
    """401 = no identity supplied. 403 = identity supplied but rejected."""

    header = req.headers.get("Authorization", "")

    if not header.startswith("Bearer "):
        return 401, "missing or malformed Authorization header"

    token = header.split(" ", 1)[1]
    expected_key = os.environ.get("API_KEY", "")

    if token != expected_key:
        return 403, "that key is not allowed here"

    return 200, None


def rate_limited(token):
    now = time.monotonic()
    timestamps = request_times[token]

    while timestamps and now - timestamps[0] >= RATE_WINDOW:
        timestamps.popleft()

    if len(timestamps) >= RATE_LIMIT:
        retry_after = max(
            1,
            int(RATE_WINDOW - (now - timestamps[0])) + 1,
        )
        return retry_after

    timestamps.append(now)
    return None


@app.get("/health")
def health():
    start = time.time()

    response = jsonify(status="ok")

    REQUESTS.labels("/health", "GET", 200).inc()
    LATENCY.labels("/health").observe(time.time() - start)

    return response


@app.get("/metrics")
def metrics():
    return generate_latest(), 200, {
        "Content-Type": CONTENT_TYPE_LATEST
    }


@app.get("/orders")
def orders():
    start = time.time()

    code, msg = authorised(request)

    if code != 200:
        REQUESTS.labels("/orders", "GET", code).inc()
        LATENCY.labels("/orders").observe(time.time() - start)
        return jsonify(error=msg), code

    token = request.headers.get("Authorization", "").split(" ", 1)[1]

    retry_after = rate_limited(token)

    if retry_after is not None:
        REQUESTS.labels("/orders", "GET", 429).inc()
        LATENCY.labels("/orders").observe(time.time() - start)

        response = jsonify(error="rate limit exceeded")
        response.status_code = 429
        response.headers["Retry-After"] = str(retry_after)
        return response

    try:
        page = int(request.args.get("page", 1))
        per_page = int(
            request.args.get("per_page", 20)
        )
    except ValueError:
        REQUESTS.labels("/orders", "GET", 400).inc()
        LATENCY.labels("/orders").observe(time.time() - start)
        return jsonify(
            error="page and per_page must be integers"
        ), 400

    if page < 1:
        REQUESTS.labels("/orders", "GET", 400).inc()
        LATENCY.labels("/orders").observe(time.time() - start)
        return jsonify(error="page must be at least 1"), 400

    if per_page < 1:
        REQUESTS.labels("/orders", "GET", 400).inc()
        LATENCY.labels("/orders").observe(time.time() - start)
        return jsonify(error="per_page must be at least 1"), 400

    per_page = min(per_page, 100)
    offset = (page - 1) * per_page

    with db() as connection:
        with connection.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) FROM orders")
            total = cursor.fetchone()[0]

            cursor.execute(
                """
                SELECT id, customer_id, drink_id, store_id,
                       qty, ordered_at, status
                FROM orders
                ORDER BY id
                LIMIT %s OFFSET %s
                """,
                (per_page, offset),
            )

            rows = cursor.fetchall()

    results = [
        {
            "id": row[0],
            "customer_id": row[1],
            "drink_id": row[2],
            "store_id": row[3],
            "qty": row[4],
            "ordered_at": (
                row[5].isoformat()
                if row[5]
                else None
            ),
            "status": row[6],
        }
        for row in rows
    ]

    response = jsonify(
        count=len(results),
        total=total,
        page=page,
        per_page=per_page,
        results=results,
    )

    REQUESTS.labels("/orders", "GET", 200).inc()
    LATENCY.labels("/orders").observe(
        time.time() - start
    )

    return response


@app.get("/stats")
def stats():
    raise NotImplementedError(
        "Phase 3: implement /stats"
    )


if __name__ == "__main__":
    app.run(port=8000)

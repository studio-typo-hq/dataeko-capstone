
"""
Simple orders API for the capstone assignment.
"""

import os
import time

import psycopg
from flask import Flask, jsonify, request
from prometheus_client import (
    Counter,
    Gauge,
    Histogram,
    generate_latest,
    CONTENT_TYPE_LATEST,
)
from api.config import API_KEY, DB_DSN, PAGE_SIZE_DEFAULT, PAGE_SIZE_MAX


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
    "Number of orders requests currently in flight",
)

# Phase 2 rate limiting:
# Maximum 10 requests in 10 seconds for each API key.
RATE_LIMIT = 10
RATE_WINDOW = 10
RATE_REQUESTS = {}


def db():
    return psycopg.connect(os.environ.get("DB_DSN", DB_DSN))


def authorised(req):
    """401 = we do not know who you are. 403 = we know, and no."""

    header = req.headers.get("Authorization", "")

    if not header.startswith("Bearer "):
        return 401, "missing or malformed Authorization header"

    token = header.split(" ", 1)[1]

    if token != API_KEY:
        return 403, "that key is not allowed here"

    return 200, None


def check_rate_limit(token):
    """Return (limited, retry_after_seconds)."""

    now = time.time()

    timestamps = RATE_REQUESTS.setdefault(token, [])

    # Remove requests older than the 10-second window.
    timestamps[:] = [
        timestamp
        for timestamp in timestamps
        if now - timestamp < RATE_WINDOW
    ]

    if len(timestamps) >= RATE_LIMIT:
        retry_after = max(
            1,
            int(RATE_WINDOW - (now - timestamps[0]) + 0.999),
        )
        return True, retry_after

    timestamps.append(now)

    return False, None


@app.get("/health")
def health():
    return jsonify(status="ok")


@app.get("/metrics")
def metrics():
    return generate_latest(), 200, {"Content-Type": CONTENT_TYPE_LATEST}


@app.get("/orders")
def orders():
    start = time.time()

    code, msg = authorised(request)

    if code != 200:
        REQUESTS.labels("/orders", "GET", code).inc()
        return jsonify(error=msg), code

    token = request.headers.get("Authorization").split(" ", 1)[1]

    limited, retry_after = check_rate_limit(token)

    if limited:
        REQUESTS.labels("/orders", "GET", 429).inc()

        return (
            jsonify(error="rate limit exceeded"),
            429,
            {"Retry-After": str(retry_after)},
        )

    page = request.args.get(
        "page",
        default=1,
        type=int,
    )

    per_page = request.args.get(
        "per_page",
        default=PAGE_SIZE_DEFAULT,
        type=int,
    )

    if page < 1:
        page = 1

    if per_page < 1:
        per_page = PAGE_SIZE_DEFAULT

    per_page = min(per_page, PAGE_SIZE_MAX)

    offset = (page - 1) * per_page

    with db() as conn:
        with conn.cursor() as cur:

            cur.execute("SELECT COUNT(*) FROM orders")
            total = cur.fetchone()[0]

            cur.execute(
                """
                SELECT
                    id,
                    customer_id,
                    drink_id,
                    store_id,
                    qty,
                    ordered_at,
                    status
                FROM orders
                ORDER BY id
                LIMIT %s OFFSET %s
                """,
                (per_page, offset),
            )

            rows = cur.fetchall()

    results = [
        {
            "id": row[0],
            "customer_id": row[1],
            "drink_id": row[2],
            "store_id": row[3],
            "qty": row[4],
            "ordered_at": row[5].isoformat(),
            "status": row[6],
        }
        for row in rows
    ]

    REQUESTS.labels("/orders", "GET", 200).inc()
    LATENCY.labels("/orders").observe(time.time() - start)

    return jsonify(
        count=len(results),
        total=total,
        page=page,
        per_page=per_page,
        results=results,
    )


@app.get("/stats")
def stats():
    # TODO (Phase 3): return the four business answers as JSON.
    raise NotImplementedError("Phase 3: implement /stats")


if __name__ == "__main__":
    app.run(port=8000)

"""
Orders API — DATAEKO capstone.

Endpoints:
- GET /health
- GET /metrics
- GET /orders
- GET /stats

Run:
    flask --app api/app.py run --port 8000
"""

import os
import time

import psycopg

from flask import Flask, jsonify, request
from prometheus_client import (
    Counter,
    Histogram,
    generate_latest,
    CONTENT_TYPE_LATEST,
)

from api.config import DB_DSN, PAGE_SIZE_DEFAULT, PAGE_SIZE_MAX


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


# In-memory rate limiter.
# Key -> list of request timestamps.
RATE_LIMIT = {}
RATE_LIMIT_COUNT = 10
RATE_LIMIT_WINDOW = 10


def db():
    return psycopg.connect(os.environ.get("DB_DSN", DB_DSN))


def authorised(req):
    """401 = we do not know who you are. 403 = we know, and no."""

    header = req.headers.get("Authorization")

    if not header:
        return 401, "missing Authorization header"

    if not header.startswith("Bearer "):
        return 401, "missing or malformed Authorization header"

    token = header.split(" ", 1)[1]

    expected_key = os.environ.get("API_KEY", "")

    if not expected_key or token != expected_key:
        return 403, "that key is not allowed here"

    return 200, None


def rate_limited(key):
    """Return True when the key has made more than 10 requests in 10 seconds."""

    now = time.time()
    cutoff = now - RATE_LIMIT_WINDOW

    timestamps = RATE_LIMIT.setdefault(key, [])

    # Keep only requests inside the current window.
    timestamps[:] = [timestamp for timestamp in timestamps if timestamp > cutoff]

    if len(timestamps) >= RATE_LIMIT_COUNT:
        return True

    timestamps.append(now)
    return False


@app.after_request
def record_latency(response):
    """Record request latency for /orders."""

    start = request.environ.get("capstone_request_start")

    if start is not None:
        LATENCY.labels(request.path).observe(time.time() - start)

    return response


@app.get("/health")
def health():
    return jsonify(status="ok")


@app.get("/metrics")
def metrics():
    return generate_latest(), 200, {"Content-Type": CONTENT_TYPE_LATEST}


@app.get("/orders")
def orders():
    start = time.time()
    request.environ["capstone_request_start"] = start

    code, msg = authorised(request)

    if code != 200:
        REQUESTS.labels("/orders", "GET", code).inc()
        return jsonify(error=msg), code

    api_key = request.headers.get("Authorization", "").split(" ", 1)[1]

    if rate_limited(api_key):
        REQUESTS.labels("/orders", "GET", 429).inc()

        response = jsonify(error="rate limit exceeded")
        response.status_code = 429
        response.headers["Retry-After"] = "10"
        return response

    try:
        page = request.args.get("page", PAGE_SIZE_DEFAULT, type=int)
        per_page = request.args.get(
            "per_page",
            PAGE_SIZE_DEFAULT,
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

        return jsonify(
            count=len(results),
            total=total,
            page=page,
            per_page=per_page,
            results=results,
        )

    except Exception:
        REQUESTS.labels("/orders", "GET", 500).inc()
        return jsonify(error="internal server error"), 500


@app.get("/stats")
def stats():
    # TODO (Phase 3): return the four business answers as JSON.
    raise NotImplementedError("Phase 3: implement /stats")


if __name__ == "__main__":
    app.run(port=8000)

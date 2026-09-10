"""
Orders API — DATAEKO capstone.

Endpoints you must finish are marked TODO. Everything else works.
Run it:  flask --app api/app.py run --port 8000
"""
import os
import time
from collections import defaultdict, deque
import psycopg
from flask import Flask, jsonify, request
from prometheus_client import Counter, Gauge, Histogram, generate_latest, CONTENT_TYPE_LATEST

from api.config import API_KEY, DB_DSN, PAGE_SIZE_DEFAULT, PAGE_SIZE_MAX

app = Flask(__name__)

RATE_LIMIT = 10
RATE_WINDOW = 10
REQUEST_TIMES = defaultdict(deque)

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

ORDERS_IN_FLIGHT = Gauge(
    "capstone_orders_in_flight",
    "Number of orders requests currently being processed",
)


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

def rate_limited(key):
    """Return Retry-After seconds when the key has exceeded its limit."""
    now = time.monotonic()
    timestamps = REQUEST_TIMES[key]

    while timestamps and now - timestamps[0] >= RATE_WINDOW:
        timestamps.popleft()

    if len(timestamps) >= RATE_LIMIT:
        retry_after = max(1, int(RATE_WINDOW - (now - timestamps[0]) + 0.999))
        return True, retry_after

    timestamps.append(now)
    return False, 0

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

    token = request.headers.get("Authorization", "").split(" ", 1)[1]
    limited, retry_after = rate_limited(token)

    if limited:
        REQUESTS.labels("/orders", "GET", 429).inc()
        return (
            jsonify(error="rate limit exceeded"),
            429,
            {"Retry-After": str(retry_after)},
        )
    ORDERS_IN_FLIGHT.inc()

    try:
        # existing pagination code
        page = request.args.get("page", 1, type=int)
        per_page = request.args.get("per_page", PAGE_SIZE_DEFAULT, type=int)

        if page < 1:
            return jsonify(error="page must be at least 1"), 400

        if per_page < 1:
            return jsonify(error="per_page must be at least 1"), 400

        per_page = min(per_page, PAGE_SIZE_MAX)
        offset = (page - 1) * per_page

        with db() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT COUNT(*) FROM orders")
                total = cur.fetchone()[0]

                cur.execute(
                    """
                    SELECT id, customer_id, drink_id, store_id,
                           qty, ordered_at, status
                    FROM orders
                    ORDER BY id
                    LIMIT %s OFFSET %s
                    """,
                    (per_page, offset),
                )

                columns = [description.name for description in cur.description]
                rows = [dict(zip(columns, row)) for row in cur.fetchall()]

        REQUESTS.labels("/orders", "GET", 200).inc()
        LATENCY.labels("/orders").observe(time.time() - start)

        return jsonify(
            count=len(rows),
            total=total,
            page=page,
            per_page=per_page,
            results=rows,
        )

    finally:
        ORDERS_IN_FLIGHT.dec()


@app.get("/stats")
def stats():
    # TODO (Phase 3): return the four business answers as JSON.
    raise NotImplementedError("Phase 3: implement /stats")


if __name__ == "__main__":
    app.run(port=8000)

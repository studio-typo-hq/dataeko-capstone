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
from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST

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
    "Number of HTTP requests currently being processed",
)

@app.before_request
def request_started():
    ORDERS_IN_FLIGHT.inc()
    request._metrics_start = time.time()


@app.after_request
def request_finished(response):
    elapsed = time.time() - request._metrics_start

    REQUESTS.labels(
        request.path,
        request.method,
        response.status_code,
    ).inc()

    LATENCY.labels(request.path).observe(elapsed)

    return response


@app.teardown_request
def request_finished_gauge(exception=None):
    ORDERS_IN_FLIGHT.dec()


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
def rate_limit_check(token):
    now = time.time()
    timestamps = REQUEST_TIMES[token]

    while timestamps and now - timestamps[0] >= RATE_WINDOW:
        timestamps.popleft()

    if len(timestamps) >= RATE_LIMIT:
        retry_after = max(1, int(RATE_WINDOW - (now - timestamps[0])))
        return False, retry_after

    timestamps.append(now)
    return True, None

@app.get("/health")
def health():
    return jsonify(status="ok")


@app.get("/metrics")
def metrics():
    return generate_latest(), 200, {"Content-Type": CONTENT_TYPE_LATEST}


@app.get("/orders")
def orders():
    code, msg = authorised(request)

    if code != 200:
        return jsonify(error=msg), code

    token = request.headers.get("Authorization").split(" ", 1)[1]

    allowed, retry_after = rate_limit_check(token)

    if not allowed:
        return (
            jsonify(error="rate limit exceeded"),
            429,
            {"Retry-After": str(retry_after)},
        )

    try:
        page = max(request.args.get("page", 1, type=int), 1)
        per_page = request.args.get(
            "per_page",
            PAGE_SIZE_DEFAULT,
            type=int,
        )
        per_page = max(1, min(per_page, PAGE_SIZE_MAX))
    except (TypeError, ValueError):
        return jsonify(error="invalid pagination parameters"), 400

    offset = (page - 1) * per_page

    with db() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM orders")
            total = cur.fetchone()[0]

            cur.execute(
                """
                SELECT *
                FROM orders
                ORDER BY id
                LIMIT %s OFFSET %s
                """,
                (per_page, offset),
            )

            rows = cur.fetchall()
            columns = [desc.name for desc in cur.description]

    results = [dict(zip(columns, row)) for row in rows]

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

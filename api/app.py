"""
Orders API — DATAEKO capstone.

Endpoints you must finish are marked TODO. Everything else works.
Run it:  flask --app api/app.py run --port 8000
"""
import os
import time
from collections import defaultdict, deque

import psycopg
from psycopg.rows import dict_row
from flask import Flask, jsonify, request
from prometheus_client import Counter, Gauge, Histogram, generate_latest, CONTENT_TYPE_LATEST

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

IN_FLIGHT = Gauge("capstone_orders_in_flight", "Orders requests currently in flight")
RATE_LIMIT = 10
RATE_WINDOW = 10
REQUEST_TIMES = defaultdict(deque)


def db():
    return psycopg.connect(os.environ.get("DB_DSN", DB_DSN), row_factory=dict_row)


def authorised(req):
    """401 = we do not know who you are. 403 = we know, and no."""
    header = req.headers.get("Authorization", "")
    if not header.startswith("Bearer "):
        return 401, "missing or malformed Authorization header"
    token = header.split(" ", 1)[1]
    if token != os.environ.get("API_KEY", API_KEY):
        return 403, "that key is not allowed here"
    return 200, None


@app.get("/health")
def health():
    return jsonify(status="ok")


@app.get("/metrics")
def metrics():
    return generate_latest(), 200, {"Content-Type": CONTENT_TYPE_LATEST}


@app.get("/orders")
def orders():
    start = time.time()
    IN_FLIGHT.inc()
    try:
        code, msg = authorised(request)
        if code != 200:
            REQUESTS.labels("/orders", "GET", code).inc()
            return jsonify(error=msg), code

        token = request.headers["Authorization"].split(" ", 1)[1]
        now = time.monotonic()
        timestamps = REQUEST_TIMES[token]
        while timestamps and now - timestamps[0] >= RATE_WINDOW:
            timestamps.popleft()
        if len(timestamps) >= RATE_LIMIT:
            REQUESTS.labels("/orders", "GET", 429).inc()
            return jsonify(error="rate limit exceeded"), 429, {"Retry-After": "10"}
        timestamps.append(now)

        try:
            page = max(1, request.args.get("page", 1, type=int))
            per_page = min(PAGE_SIZE_MAX, max(1, request.args.get("per_page", PAGE_SIZE_DEFAULT, type=int)))
        except (TypeError, ValueError):
            REQUESTS.labels("/orders", "GET", 400).inc()
            return jsonify(error="page and per_page must be integers"), 400
        offset = (page - 1) * per_page
        with db() as connection, connection.cursor() as cursor:
            cursor.execute("SELECT count(*) AS total FROM orders")
            total = cursor.fetchone()["total"]
            cursor.execute(
                """
                SELECT id, customer_id, drink_id, store_id, qty, ordered_at, status
                FROM orders ORDER BY id LIMIT %s OFFSET %s
                """,
                (per_page, offset),
            )
            results = cursor.fetchall()
        REQUESTS.labels("/orders", "GET", 200).inc()
        return jsonify(count=len(results), total=total, page=page, per_page=per_page, results=results)
    finally:
        LATENCY.labels("/orders").observe(time.time() - start)
        IN_FLIGHT.dec()


@app.get("/stats")
def stats():
    code, msg = authorised(request)
    if code != 200:
        return jsonify(error=msg), code
    with db() as connection, connection.cursor() as cursor:
        cursor.execute("SELECT count(*) AS value FROM orders WHERE status = 'collected'")
        collected = cursor.fetchone()["value"]
        cursor.execute("SELECT count(*) AS value FROM drinks d WHERE NOT EXISTS (SELECT 1 FROM orders o WHERE o.drink_id = d.id)")
        never_ordered = cursor.fetchone()["value"]
        cursor.execute("SELECT count(*) AS value FROM orders o LEFT JOIN deliveries d ON d.order_id = o.id WHERE d.id IS NULL")
        undelivered = cursor.fetchone()["value"]
        cursor.execute("SELECT count(*) AS value FROM (SELECT customer_id FROM orders GROUP BY customer_id HAVING count(*) > 25) loyal")
        loyal_customers = cursor.fetchone()["value"]
    return jsonify(collected_orders=collected, never_ordered_drinks=never_ordered, undelivered_orders=undelivered, loyal_customers=loyal_customers)


if __name__ == "__main__":
    app.run(port=8000)

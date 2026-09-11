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

from api.config import DB_DSN, PAGE_SIZE_DEFAULT, PAGE_SIZE_MAX

app = Flask(__name__)
RATE_LIMIT = 10
RATE_WINDOW = 10
request_times = defaultdict(deque)

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

def db():
    return psycopg.connect(os.environ.get("DB_DSN", DB_DSN))

def rate_limited(token):
    now = time.time()
    times = request_times[token]

    while times and now - times[0] >= RATE_WINDOW:
        times.popleft()

    if len(times) >= RATE_LIMIT:
        retry_after = max(1, int(RATE_WINDOW - (now - times[0])) + 1)
        return True, retry_after

    times.append(now)
    return False, 0

def authorised(req):
    """401 = we do not know who you are. 403 = we know, and no."""
    header = req.headers.get("Authorization", "")
    if not header.startswith("Bearer "):
        return 401, "missing or malformed Authorization header"
    
    token = header.split(" ", 1)[1]
    
    if token != os.environ.get("API_KEY", ""):
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
        page = max(1, request.args.get("page", 1, type=int))
        per_page = request.args.get(
            "per_page",
            PAGE_SIZE_DEFAULT,
            type=int,
        )
        per_page = max(1, min(per_page, PAGE_SIZE_MAX))

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

    finally:
        ORDERS_IN_FLIGHT.dec()
        LATENCY.labels("/orders").observe(time.time() - start)


@app.get("/stats")
def stats():
    # TODO (Phase 3): return the four business answers as JSON.
    raise NotImplementedError("Phase 3: implement /stats")


if __name__ == "__main__":
    app.run(port=8000)

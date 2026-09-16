"""
Orders API — DATAEKO capstone.

Endpoints you must finish are marked TODO. Everything else works.
Run it:  flask --app api/app.py run --port 8000
"""
import collections
import os
import time
import psycopg
from flask import Flask, jsonify, request
from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST

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
    "Number of requests currently in flight",
)

# In-memory rate limiting: 10 requests per 10 seconds per key
_RATE_LIMIT_STORE = collections.defaultdict(collections.deque)
RATE_LIMIT_WINDOW = 10
RATE_LIMIT_MAX = 10


def check_rate_limit(key: str):
    now = time.time()
    dq = _RATE_LIMIT_STORE[key]
    while dq and dq[0] <= now - RATE_LIMIT_WINDOW:
        dq.popleft()
    if len(dq) >= RATE_LIMIT_MAX:
        retry_after = max(1, int(RATE_LIMIT_WINDOW - (now - dq[0])) + 1)
        return False, retry_after
    dq.append(now)
    return True, 0


def db():
    return psycopg.connect(os.environ.get("DB_DSN", DB_DSN))


def authorised(req):
    """401 = we do not know who you are. 403 = we know, and no."""
    header = req.headers.get("Authorization", "")
    if not header.startswith("Bearer "):
        return 401, "missing or malformed Authorization header", None
    token = header.split(" ", 1)[1]
    expected = os.environ.get("API_KEY", API_KEY)
    if token != expected:
        return 403, "that key is not allowed here", token
    return 200, None, token


@app.get("/health")
def health():
    REQUESTS.labels("/health", "GET", 200).inc()
    return jsonify(status="ok")


@app.get("/metrics")
def metrics():
    return generate_latest(), 200, {"Content-Type": CONTENT_TYPE_LATEST}


@app.get("/orders")
def orders():
    IN_FLIGHT.inc()
    start = time.time()
    try:
        code, msg, token = authorised(request)
        if code != 200:
            REQUESTS.labels("/orders", "GET", code).inc()
            return jsonify(error=msg), code

        allowed, retry_after = check_rate_limit(token)
        if not allowed:
            REQUESTS.labels("/orders", "GET", 429).inc()
            resp = jsonify(error="rate limit exceeded")
            resp.headers["Retry-After"] = str(retry_after)
            return resp, 429

        page = request.args.get("page", 1, type=int)
        per_page = request.args.get("per_page", PAGE_SIZE_DEFAULT, type=int)

        if page < 1:
            REQUESTS.labels("/orders", "GET", 400).inc()
            return jsonify(error="page must be >= 1"), 400

        if per_page < 1:
            REQUESTS.labels("/orders", "GET", 400).inc()
            return jsonify(error="per_page must be >= 1"), 400

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

                rows = cur.fetchall()

        orders_data = [
            {
                "id": row[0],
                "customer_id": row[1],
                "drink_id": row[2],
                "store_id": row[3],
                "qty": row[4],
                "ordered_at": row[5].isoformat() if hasattr(row[5], "isoformat") else str(row[5]),
                "status": row[6],
            }
            for row in rows
        ]

        REQUESTS.labels("/orders", "GET", 200).inc()
        return jsonify(
            page=page,
            per_page=per_page,
            count=len(orders_data),
            total=total,
            results=orders_data,
            orders=orders_data,
        ), 200

    except Exception as exc:
        REQUESTS.labels("/orders", "GET", 500).inc()
        return jsonify(error=str(exc)), 500
    finally:
        LATENCY.labels("/orders").observe(time.time() - start)
        IN_FLIGHT.dec()


@app.get("/stats")
def stats():
    """Return the four business query answers as JSON."""
    try:
        with db() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT s.city, SUM(o.qty * d.price_inr) AS total_revenue
                    FROM orders o
                    JOIN drinks d ON d.id = o.drink_id
                    JOIN stores s ON s.id = o.store_id
                    WHERE o.status = 'collected'
                    GROUP BY s.city
                    ORDER BY total_revenue DESC;
                    """
                )
                revenue_by_city = [{"city": r[0], "total_revenue": float(r[1])} for r in cur.fetchall()]

                cur.execute(
                    """
                    SELECT d.name
                    FROM drinks d
                    LEFT JOIN orders o ON o.drink_id = d.id
                    WHERE o.id IS NULL
                    ORDER BY d.name;
                    """
                )
                never_ordered = [r[0] for r in cur.fetchall()]

                cur.execute(
                    """
                    SELECT COUNT(*)
                    FROM orders o
                    LEFT JOIN deliveries d ON d.order_id = o.id
                    WHERE d.id IS NULL;
                    """
                )
                undelivered = cur.fetchone()[0]

                cur.execute(
                    """
                    SELECT c.id, c.name, COUNT(o.id) AS order_count, SUM(o.qty * d.price_inr) AS total_spend
                    FROM customers c
                    JOIN orders o ON o.customer_id = c.id
                    JOIN drinks d ON d.id = o.drink_id
                    GROUP BY c.id, c.name
                    HAVING COUNT(o.id) > 25
                    ORDER BY order_count DESC, total_spend DESC;
                    """
                )
                loyal_customers = [
                    {"id": r[0], "name": r[1], "order_count": r[2], "total_spend": float(r[3])}
                    for r in cur.fetchall()
                ]

        return jsonify(
            revenue_by_city=revenue_by_city,
            never_ordered=never_ordered,
            undelivered=undelivered,
            loyal_customers=loyal_customers,
        ), 200
    except Exception as exc:
        return jsonify(error=str(exc)), 500


if __name__ == "__main__":
    app.run(port=8000)

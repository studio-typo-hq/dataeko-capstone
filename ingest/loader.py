"""
CSV -> Postgres loader.

Reads data/orders.csv, validates each row, inserts the good ones and writes the
bad ones to evidence/rejected.csv with a reason.

The file has deliberately malformed rows. It must NOT crash on them.
"""
import csv
import sys
from pathlib import Path
import os
import psycopg

import requests
from datetime import datetime

def fetch_reference(url):
    """Fetch the drinks reference list from the running API."""
    # DEFECT: no timeout. Week 2 told you what happens on the day the
    # server accepts the connection and then says nothing at all.
    response = requests.get(url, timeout=10)
    response.raise_for_status()
    return response.json()


def read_rows(path):
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        yield from reader
    # raise NotImplementedError("Phase 1: implement read_rows")


def validate(row):
    required = {
        "order_id",
        "customer_id",
        "drink_id",
        "store_id",
        "qty",
        "ordered_at",
        "status",
    }

    if set(row.keys()) != required:
        return False, "invalid columns"

    for field in ["order_id", "customer_id", "drink_id", "store_id"]:
        if not row[field]:
            return False, f"{field} is empty"
        try:
            int(row[field])
        except ValueError:
            return False, f"{field} is not an integer"

    try:
        qty = int(row["qty"])
    except ValueError:
        return False, "qty is not an integer"

    if qty <= 0:
        return False, "qty must be positive"

    try:
        datetime.fromisoformat(row["ordered_at"])
    except ValueError:
        return False, "ordered_at is invalid"

    if row["status"] not in {
        "placed",
        "ready",
        "collected",
        "cancelled",
    }:
        return False, "invalid status"

    return True, ""
    # raise NotImplementedError("Phase 1: implement validate")


def load(path):
    dsn = os.environ.get(
        "DB_DSN",
        "postgresql://postgres:password@localhost:5434/capstone",
    )
    rejected_path = Path("evidence/rejected.csv")
    rejected_path.parent.mkdir(parents=True, exist_ok=True)

    good_count = 0
    rejected = []

    rows = list(read_rows(path))

    with psycopg.connect(dsn) as conn:
        # Load valid foreign-key IDs once so malformed references
        # can be rejected without aborting the transaction.
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM customers")
            customer_ids = {row[0] for row in cur.fetchall()}

            cur.execute("SELECT id FROM drinks")
            drink_ids = {row[0] for row in cur.fetchall()}

            cur.execute("SELECT id FROM stores")
            store_ids = {row[0] for row in cur.fetchall()}

            for row in rows:
                ok, reason = validate(row)

                if ok:
                    try:
                        customer_id = int(row["customer_id"])
                        drink_id = int(row["drink_id"])
                        store_id = int(row["store_id"])

                        if customer_id not in customer_ids:
                            ok = False
                            reason = "customer_id does not exist"
                        elif drink_id not in drink_ids:
                            ok = False
                            reason = "drink_id does not exist"
                        elif store_id not in store_ids:
                            ok = False
                            reason = "store_id does not exist"

                        if ok:
                            cur.execute(
                                """
                                INSERT INTO orders
                                    (customer_id, drink_id, store_id, qty,
                                     ordered_at, status)
                                VALUES (%s, %s, %s, %s, %s, %s)
                                """,
                                (
                                    customer_id,
                                    drink_id,
                                    store_id,
                                    int(row["qty"]),
                                    row["ordered_at"],
                                    row["status"],
                                ),
                            )
                            good_count += 1

                    except (ValueError, TypeError) as exc:
                        ok = False
                        reason = str(exc)

                if not ok:
                    rejected_row = {
                        field: row.get(field, "")
                        for field in [
                            "order_id",
                            "customer_id",
                            "drink_id",
                            "store_id",
                            "qty",
                            "ordered_at",
                            "status",
                        ]
                    }
                    rejected_row["reason"] = reason
                    rejected.append(rejected_row)

    fieldnames = [
        "order_id",
        "customer_id",
        "drink_id",
        "store_id",
        "qty",
        "ordered_at",
        "status",
        "reason",
    ]

    with open(rejected_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rejected)

    print(f"loaded {good_count} rows")
    print(f"rejected {len(rejected)} rows -> {rejected_path}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("usage: python ingest/loader.py <csv-path>", file=sys.stderr)
        sys.exit(2)
    load(Path(sys.argv[1]))

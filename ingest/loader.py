"""
CSV -> Postgres loader.

Reads data/orders.csv, validates each row, inserts the good ones and writes the
bad ones to evidence/rejected.csv with a reason.

The file has deliberately malformed rows. It must NOT crash on them.
"""
import csv
import sys
from pathlib import Path

import requests


def fetch_reference(url):
    """Fetch the drinks reference list from the running API."""
    # DEFECT: no timeout. Week 2 told you what happens on the day the
    # server accepts the connection and then says nothing at all.
    response = requests.get(url, timeout=10)
    response.raise_for_status()
    return response.json()


def read_rows(path):
    """Yield one dictionary per CSV row using the csv module."""
    expected_fields = [
        "order_id",
        "customer_id",
        "drink_id",
        "store_id",
        "qty",
        "ordered_at",
        "status",
    ]

    with open(path, newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)

        for row in reader:
            if None in row:
                row["_row_error"] = "row has too many fields"
                row.pop(None, None)
            elif any(row.get(field) is None for field in expected_fields):
                row["_row_error"] = "row has too few fields"

            yield row


def validate(row):
    """Validate a CSV row and return (ok, reason)."""
    if row.get("_row_error"):
        return False, row["_row_error"]

    required_fields = {
        "order_id",
        "customer_id",
        "drink_id",
        "store_id",
        "qty",
        "ordered_at",
        "status",
    }

    if set(row.keys()) != required_fields:
        return False, "row has incorrect fields"

    for field in required_fields:
        value = row.get(field)
        if value is None or not str(value).strip():
            return False, f"missing {field}"

    try:
        qty = int(row["qty"])
    except (TypeError, ValueError):
        return False, "qty must be an integer"

    if qty <= 0:
        return False, "qty must be greater than zero"

    try:
        from datetime import datetime
        datetime.fromisoformat(row["ordered_at"])
    except (TypeError, ValueError):
        return False, "ordered_at must be a valid timestamp"

    valid_statuses = {"placed", "ready", "collected", "cancelled"}
    if row["status"] not in valid_statuses:
        return False, f"invalid status: {row['status']}"

    return True, ""


def load(path):
    """Insert valid rows into Postgres and write rejected rows to evidence."""
    import os

    import psycopg

    dsn = os.environ.get(
        "DB_DSN",
        "postgresql://postgres:secret@localhost:5432/capstone",
    )

    rows = list(read_rows(path))
    rejected = []
    inserted = 0

    evidence_dir = Path("evidence")
    evidence_dir.mkdir(parents=True, exist_ok=True)
    rejected_path = evidence_dir / "rejected.csv"

    with psycopg.connect(dsn) as conn:
        with conn.cursor() as cur:
            for row in rows:
                ok, reason = validate(row)

                if not ok:
                    rejected.append((row, reason))
                    continue

                try:
                    drink_id = int(row["drink_id"])
                except (TypeError, ValueError):
                    rejected.append((row, "drink_id must be an integer"))
                    continue

                cur.execute(
                    "SELECT 1 FROM drinks WHERE id = %s",
                    (drink_id,),
                )

                if cur.fetchone() is None:
                    rejected.append((row, f"drink_id {drink_id} does not exist"))
                    continue

                cur.execute(
                    """
                    INSERT INTO orders
                        (customer_id, drink_id, store_id, qty, ordered_at, status)
                    VALUES
                        (%s, %s, %s, %s, %s, %s)
                    """,
                    (
                        int(row["customer_id"]),
                        drink_id,
                        int(row["store_id"]),
                        int(row["qty"]),
                        row["ordered_at"],
                        row["status"],
                    ),
                )
                inserted += 1

    with rejected_path.open("w", newline="", encoding="utf-8") as handle:
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
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()

        for row, reason in rejected:
            writer.writerow({
                "order_id": row.get("order_id", ""),
                "customer_id": row.get("customer_id", ""),
                "drink_id": row.get("drink_id", ""),
                "store_id": row.get("store_id", ""),
                "qty": row.get("qty", ""),
                "ordered_at": row.get("ordered_at", ""),
                "status": row.get("status", ""),
                "reason": reason,
            })

    print(f"read {len(rows)} rows")
    print(f"inserted {inserted}")
    print(f"rejected {len(rejected)} -> {rejected_path}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("usage: python ingest/loader.py <csv-path>", file=sys.stderr)
        sys.exit(2)
    load(Path(sys.argv[1]))

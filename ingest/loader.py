"""
CSV -> Postgres loader.

Reads data/orders.csv, validates each row, inserts the
good ones and writes the bad ones to evidence/rejected.csv
with a reason.

The file has deliberately malformed rows. It must NOT crash
on them.
"""

import csv
import sys
from pathlib import Path
from datetime import datetime

import psycopg2
import requests


DB_DSN = "postgresql://postgres:secret@localhost:5433/capstone"

def fetch_reference(url):
    """Fetch the drinks reference list from the running API."""
    # DEFECT: no timeout. Week 2 told you what happens on the day the
    # server accepts the connection and then says nothing at all.
    response = requests.get(url, timeout=5)
    response.raise_for_status()
    return response.json()


def read_rows(path):
    """Yield one dictionary for each row in the CSV file."""
    with open(path, newline="", encoding="utf-8") as file:
        reader = csv.DictReader(file)
        yield from reader

def validate(row):
    """Validate a single CSV row and return (ok, reason)."""
    required_fields = [
        "order_id",
        "customer_id",
        "drink_id",
        "store_id",
        "qty",
        "ordered_at",
        "status",
    ]

    for field in required_fields:
        if not row.get(field):
            return False, f"{field} is required"

    try:
        qty = int(row["qty"])
        if qty <= 0:
            return False, "qty must be greater than 0"
    except (TypeError, ValueError):
        return False, "qty must be an integer"

    try:
        from datetime import datetime

        datetime.fromisoformat(row["ordered_at"])
    except (TypeError, ValueError):
        return False, "ordered_at must be a valid datetime"

    allowed_statuses = {"placed", "ready", "collected", "cancelled"}

    if row["status"] not in allowed_statuses:
        return False, f"invalid status: {row['status']}"

    return True, ""

def load(path):
    """Validate CSV rows, insert valid rows and write rejected rows."""

    rows = list(read_rows(path))
    rejected = []
    valid_rows = []

    for row in rows:
        if None in row:
            rejected.append({
                **row,
                "reason": "row has too many fields",
            })
            continue

        required_fields = [
            "order_id",
            "customer_id",
            "drink_id",
            "store_id",
            "qty",
            "ordered_at",
            "status",
        ]

        if not all(field in row for field in required_fields):
            rejected.append({
                **row,
                "reason": "row has too few fields",
            })
            continue

        ok, reason = validate(row)

        if ok:
            valid_rows.append(row)
        else:
            rejected.append({
                **row,
                "reason": reason,
            })

    connection = psycopg2.connect(DB_DSN)

    try:
        with connection:
            with connection.cursor() as cursor:

                checked_rows = []

                for row in valid_rows:
                    cursor.execute(
                        "SELECT 1 FROM drinks WHERE id = %s",
                        (int(row["drink_id"]),),
                    )

                    if cursor.fetchone() is None:
                        rejected.append({
                            **row,
                            "reason": "drink_id does not exist",
                        })
                        continue

                    checked_rows.append(row)

                for row in checked_rows:
                    cursor.execute(
                        """
                        INSERT INTO orders
                        (id, customer_id, drink_id, store_id, qty,
                         ordered_at, status)
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                        """,
                        (
                            int(row["order_id"]),
                            int(row["customer_id"]),
                            int(row["drink_id"]),
                            int(row["store_id"]),
                            int(row["qty"]),
                            row["ordered_at"],
                            row["status"],
                        ),
                    )

    finally:
        connection.close()

    output = Path("evidence/rejected.csv")
    output.parent.mkdir(parents=True, exist_ok=True)

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

    with output.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=fieldnames,
            extrasaction="ignore",
        )
        writer.writeheader()
        writer.writerows(rejected)

    print(f"read {len(rows)} rows")
    print(f"inserted {len(checked_rows)}")
    print(f"rejected {len(rejected)} -> {output}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("usage: python ingest/loader.py <csv-path>", file=sys.stderr)
        sys.exit(2)

    load(Path(sys.argv[1]))

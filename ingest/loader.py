"""
CSV -> Postgres loader.

Reads data/orders.csv, validates each row, inserts the
good ones and writes the bad ones to evidence/rejected.csv with a reason.

The file has deliberately malformed rows. It must NOT crash on them.
"""

import csv
import os
import sys
from pathlib import Path

import psycopg
import requests


def fetch_reference(url):
    """Fetch the drinks reference list from the running API."""
    response = requests.get(url, timeout=10)
    response.raise_for_status()
    return response.json()


def read_rows(path):
    """Yield one dict per CSV row using the csv module."""
    with open(path, newline="", encoding="utf-8") as file:
        reader = csv.DictReader(file)
        yield from reader


def validate(row):
    """Return (ok, reason) after validating a CSV row."""
    if not row.get("customer_id"):
        return False, "customer_id is required"

    try:
        qty = int(row.get("qty", ""))
        if qty <= 0:
            return False, "qty must be greater than 0"
    except (ValueError, TypeError):
        return False, "qty must be an integer"

    try:
        from datetime import datetime
        datetime.fromisoformat(row.get("ordered_at", ""))
    except (ValueError, TypeError):
        return False, "ordered_at must be a valid date/time"

    if row.get("status") not in {"placed"}:
        return False, "invalid status"

    return True, ""


def load(path):
    """Insert good rows, write rejects, and print a summary."""
    rows = list(read_rows(path))

    rejected_path = Path("evidence/rejected.csv")
    rejected_path.parent.mkdir(parents=True, exist_ok=True)

    inserted = 0
    rejected = 0

    with open(rejected_path, "w", newline="", encoding="utf-8") as file:
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

        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()

        with psycopg.connect(
            os.environ.get(
                "DB_DSN",
                "postgresql://postgres:secret@localhost:5432/capstone",
            )
        ) as conn:
            with conn.cursor() as cur:
                for row in rows:

                    # Reject rows with unexpected extra CSV columns.
                    if None in row:
                        clean_row = {
                            key: row.get(key)
                            for key in fieldnames
                            if key != "reason"
                        }
                        clean_row["reason"] = "unexpected extra columns"
                        writer.writerow(clean_row)
                        rejected += 1
                        continue

                    # Validate normal CSV fields.
                    ok, reason = validate(row)

                    if not ok:
                        writer.writerow({**row, "reason": reason})
                        rejected += 1
                        continue

                    # Check that the referenced drink exists.
                    cur.execute(
                        "SELECT 1 FROM drinks WHERE id = %s",
                        (int(row["drink_id"]),),
                    )

                    if cur.fetchone() is None:
                        writer.writerow(
                            {**row, "reason": "drink_id does not exist"}
                        )
                        rejected += 1
                        continue

                    # Insert valid row.
                    cur.execute(
                        """
                        INSERT INTO orders
                            (id, customer_id, drink_id, store_id, qty, ordered_at, status)
                        VALUES
                            (%s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (id) DO NOTHING
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

                    if cur.rowcount == 1:
                        inserted += 1

    print(f"read {len(rows)} rows")
    print(f"inserted {inserted}")
    print(f"rejected {rejected} -> {rejected_path}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(
            "usage: python ingest/loader.py <csv-path>",
            file=sys.stderr,
        )
        sys.exit(2)

    load(Path(sys.argv[1]))

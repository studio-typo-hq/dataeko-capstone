"""
CSV -> Postgres loader.

Reads data/orders.csv, validates each row, inserts the good ones and writes the
bad ones to evidence/rejected.csv with a reason.

The file has deliberately malformed rows. It must NOT crash on them.
"""

import csv
import os
import sys
from datetime import datetime
from pathlib import Path

import psycopg
import requests


DB_DSN = os.environ.get(
    "DB_DSN",
    "postgresql://postgres:secret@localhost:5432/capstone",
)


def fetch_reference(url):
    """Fetch the drinks reference list from the running API."""
    response = requests.get(url, timeout=10)
    response.raise_for_status()
    return response.json()


def read_rows(path):
    """Yield one dictionary for each CSV data row."""
    with Path(path).open("r", newline="", encoding="utf-8") as csv_file:
        reader = csv.DictReader(csv_file)

        for row in reader:
            yield row


def validate(row):
    """Return (True, "") for a valid row or (False, reason) for an invalid row."""

    # A row with more columns than the header gets a None key from DictReader.
    if None in row:
        return False, "row has too many fields"

    required_fields = [
        "order_id",
        "customer_id",
        "drink_id",
        "store_id",
        "qty",
        "ordered_at",
        "status",
    ]

    # A row with fewer columns will be missing one or more fields.
    for field in required_fields:
        if field not in row:
            return False, "row has too few fields"

        if not row[field] or not row[field].strip():
            return False, f"{field} is required"

    # IDs must be positive integers.
    for field in ["order_id", "customer_id", "drink_id", "store_id"]:
        try:
            value = int(row[field])
        except (TypeError, ValueError):
            return False, f"{field} must be an integer"

        if value <= 0:
            return False, f"{field} must be greater than 0"

    # Quantity must be a positive integer.
    try:
        qty = int(row["qty"])
    except (TypeError, ValueError):
        return False, "qty must be an integer"

    if qty <= 0:
        return False, "qty must be greater than 0"

    # ordered_at must be a valid ISO-8601 datetime.
    try:
        datetime.fromisoformat(row["ordered_at"])
    except (TypeError, ValueError):
        return False, "ordered_at must be a valid ISO-8601 datetime"

    # Must match the database CHECK constraint.
    allowed_statuses = {"placed", "ready", "collected", "cancelled"}

    if row["status"] not in allowed_statuses:
        return False, f"invalid status: {row['status']}"

    return True, ""


def load(path):
    """Insert good rows, write rejects, and print a summary."""

    rows = list(read_rows(path))
    rejected = []
    inserted = 0

    with psycopg.connect(DB_DSN) as conn:
        with conn.cursor() as cur:

            for row in rows:
                ok, reason = validate(row)

                if not ok:
                    rejected.append((row, reason))
                    continue

                # Check the referenced drink before attempting the insert.
                cur.execute(
                    "SELECT 1 FROM drinks WHERE id = %s",
                    (int(row["drink_id"]),),
                )

                if cur.fetchone() is None:
                    rejected.append((row, "drink_id does not reference an existing drink"))
                    continue

                try:
                    cur.execute(
                        """
                        INSERT INTO orders
                            (id, customer_id, drink_id, store_id,
                             qty, ordered_at, status)
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

                except psycopg.Error as exc:
                    rejected.append((row, f"database error: {exc}"))
                    conn.rollback()

    evidence_dir = Path("evidence")
    evidence_dir.mkdir(parents=True, exist_ok=True)

    rejected_path = evidence_dir / "rejected.csv"

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

    with rejected_path.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        writer.writeheader()

        for row, reason in rejected:
            output_row = {
                field: row.get(field, "")
                for field in fieldnames[:-1]
            }
            output_row["reason"] = reason
            writer.writerow(output_row)

    print(f"read {len(rows)} rows")
    print(f"inserted {inserted}")
    print(f"rejected {len(rejected)} -> {rejected_path}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("usage: python ingest/loader.py <csv-path>", file=sys.stderr)
        sys.exit(2)

    load(Path(sys.argv[1]))

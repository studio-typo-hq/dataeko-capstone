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


def fetch_reference(url):
    """Fetch the drinks reference list from the running API."""
    response = requests.get(url, timeout=10)
    response.raise_for_status()
    return response.json()


def read_rows(path):
    """Yield one dictionary per CSV row using the csv module."""
    fields = [
        "order_id",
        "customer_id",
        "drink_id",
        "store_id",
        "qty",
        "ordered_at",
        "status",
    ]

    with Path(path).open(newline="", encoding="utf-8") as f:
        reader = csv.reader(f)

        # Skip the CSV header.
        next(reader, None)

        for values in reader:
            row = dict(zip(fields, values))

            # Preserve missing fields so validate() can reject them.
            if len(values) < len(fields):
                for field in fields[len(values):]:
                    row[field] = None

            # Preserve extra columns so validate() can reject them.
            if len(values) > len(fields):
                row["__extra_columns__"] = values[len(fields):]

            yield row


def validate(row):
    """Return (ok, reason) for an order row."""

    required = [
        "order_id",
        "customer_id",
        "drink_id",
        "store_id",
        "qty",
        "ordered_at",
        "status",
    ]

    # Check required fields.
    for field in required:
        if field not in row or row[field] in (None, ""):
            return False, f"missing {field}"

    # Reject rows with extra columns.
    if "__extra_columns__" in row:
        return False, "too many columns"

    # These fields must contain integers.
    for field in ("order_id", "customer_id", "drink_id", "store_id"):
        try:
            int(row[field])
        except (TypeError, ValueError):
            return False, f"invalid {field}"

    # Quantity must be a positive integer.
    try:
        qty = int(row["qty"])
    except (TypeError, ValueError):
        return False, "invalid qty"

    if qty <= 0:
        return False, "qty must be greater than 0"

    # Timestamp must be parseable.
    try:
        datetime.fromisoformat(row["ordered_at"])
    except (TypeError, ValueError):
        return False, "invalid ordered_at"

    # Match the database CHECK constraint.
    valid_statuses = {
        "placed",
        "ready",
        "collected",
        "cancelled",
    }

    if row["status"] not in valid_statuses:
        return False, "invalid status"

    return True, ""


def load(path):
    """Insert good rows, write rejects, and print a summary."""

    dsn = os.getenv(
        "DB_DSN",
        "postgresql://postgres:secret@localhost:5432/capstone",
    )

    rows = list(read_rows(path))
    rejected = []
    good_rows = []

    with psycopg.connect(dsn) as conn:
        with conn.cursor() as cur:

            # Get existing drink IDs so invalid foreign-key references
            # can be rejected before inserting orders.
            cur.execute("SELECT id FROM drinks")
            drink_ids = {row[0] for row in cur.fetchall()}

            for row in rows:
                ok, reason = validate(row)

                if not ok:
                    rejected.append((row, reason))
                    continue

                drink_id = int(row["drink_id"])

                if drink_id not in drink_ids:
                    rejected.append(
                        (row, "drink_id does not exist")
                    )
                    continue

                good_rows.append(row)

            # Insert valid orders.
            #
            # IMPORTANT:
            # We intentionally do NOT insert order_id into orders.id.
            # The database already contains 400,000 seeded orders, so
            # PostgreSQL must generate new IDs using the serial column.
            for row in good_rows:
                cur.execute(
                    """
                    INSERT INTO orders
                        (
                            customer_id,
                            drink_id,
                            store_id,
                            qty,
                            ordered_at,
                            status
                        )
                    VALUES
                        (%s, %s, %s, %s, %s, %s)
                    """,
                    (
                        int(row["customer_id"]),
                        int(row["drink_id"]),
                        int(row["store_id"]),
                        int(row["qty"]),
                        row["ordered_at"],
                        row["status"],
                    ),
                )

    # Write rejected rows after the database transaction succeeds.
    evidence_dir = Path("evidence")
    evidence_dir.mkdir(parents=True, exist_ok=True)

    fields = [
        "order_id",
        "customer_id",
        "drink_id",
        "store_id",
        "qty",
        "ordered_at",
        "status",
        "reason",
    ]

    with (evidence_dir / "rejected.csv").open(
        "w",
        newline="",
        encoding="utf-8",
    ) as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()

        for row, reason in rejected:
            output_row = {
                field: row.get(field)
                for field in fields[:-1]
            }
            output_row["reason"] = reason
            writer.writerow(output_row)

    print(f"read {len(rows)} rows")
    print(f"inserted {len(good_rows)}")
    print(f"rejected {len(rejected)} -> evidence/rejected.csv")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("usage: python ingest/loader.py <csv-path>", file=sys.stderr)
        sys.exit(2)

    load(Path(sys.argv[1]))
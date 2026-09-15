

import csv
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
    with open(path, newline="", encoding="utf-8") as file:
        reader = csv.DictReader(file)

        for row in reader:
            yield row


def validate(row):
    """Return (ok, reason) for a CSV row."""

    required_fields = [
        "order_id",
        "customer_id",
        "drink_id",
        "store_id",
        "qty",
        "ordered_at",
        "status",
    ]

    # Reject rows containing extra CSV columns.
    if None in row:
        return False, "extra CSV field"

    # Check required fields.
    for field in required_fields:
        value = row.get(field)

        if value is None or not str(value).strip():
            return False, f"{field} is required"

    # Check integer fields.
    integer_fields = [
        "order_id",
        "customer_id",
        "drink_id",
        "store_id",
        "qty",
    ]

    for field in integer_fields:
        try:
            value = int(row[field])
        except (ValueError, TypeError):
            return False, f"{field} must be an integer"

        if field == "qty" and value <= 0:
            return False, "qty must be greater than 0"

        # The seed data defines drink IDs from 1 through 18.

    if not 1 <= int(row["drink_id"]) <= 18:
        return False, "drink_id is outside the valid range"


    # Check date/time format.
    try:
        datetime.fromisoformat(row["ordered_at"])
    except (ValueError, TypeError):
        return False, "ordered_at must be a valid ISO datetime"

    # Check allowed order statuses.
    valid_statuses = {
        "placed",
        "ready",
        "collected",
        "cancelled",
    }

    if row["status"] not in valid_statuses:
        return False, f"invalid status: {row['status']}"

    return True, ""


def load(path):
    """Insert valid rows and write rejected rows to evidence/rejected.csv."""

    database_url = "postgresql://aditya@localhost:5432/capstone"

    rows = list(read_rows(path))
    valid_rows = []
    rejected_rows = []

    for row in rows:
        ok, reason = validate(row)

        if ok:
            valid_rows.append(row)
        else:
            rejected_rows.append((row, reason))

    # Create evidence directory if it doesn't exist.
    Path("evidence").mkdir(exist_ok=True)

    # Write rejected rows.
        # Write rejected rows.
    rejected_path = Path("evidence/rejected.csv")

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

    with rejected_path.open(
        "w",
        newline="",
        encoding="utf-8",
    ) as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()

        for row, reason in rejected_rows:
            output = {
                field: row.get(field, "")
                for field in fieldnames
                if field != "reason"
            }
            output["reason"] = reason
            writer.writerow(output)

    # Insert valid rows into PostgreSQL.
    # Insert valid rows into PostgreSQL.
    inserted = 0

    with psycopg.connect(database_url) as connection:
        with connection.cursor() as cursor:
            for row in valid_rows:
                cursor.execute(
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

                inserted += 1

        connection.commit()

    print(
        f"read={len(rows)} "
        f"inserted={inserted} "
        f"rejected={len(rejected_rows)}"
    )


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(
            "usage: python ingest/loader.py <csv-path>",
            file=sys.stderr,
        )
        sys.exit(2)

    load(Path(sys.argv[1]))
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

# Allow `python ingest/loader.py ...` to import project packages as well as
# imports made when the module is loaded by pytest.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from api.config import DB_DSN


FIELDS = ["order_id", "customer_id", "drink_id", "store_id", "qty", "ordered_at", "status"]
STATUSES = {"placed", "ready", "collected", "cancelled"}


def fetch_reference(url):
    """Fetch the drinks reference list from the running API."""
    # DEFECT: no timeout. Week 2 told you what happens on the day the
    # server accepts the connection and then says nothing at all.
    response = requests.get(url, timeout=10)
    response.raise_for_status()
    return response.json()


def read_rows(path):
    """Yield one dictionary for every row in a CSV file."""
    with Path(path).open(newline="", encoding="utf-8-sig") as source:
        yield from csv.DictReader(source)


def validate(row):
    """Return whether a row is valid and explain every rejection."""
    if set(row) != set(FIELDS) or None in row or row.get(None) is not None:
        return False, "row must contain exactly the expected fields"

    for field in ("order_id", "customer_id", "drink_id", "store_id"):
        if not row[field].strip():
            return False, f"{field} is required"
        try:
            if int(row[field]) <= 0:
                return False, f"{field} must be positive"
        except ValueError:
            return False, f"{field} must be an integer"

    limits = {"customer_id": 20000, "drink_id": 18, "store_id": 6}
    for field, maximum in limits.items():
        if int(row[field]) > maximum:
            return False, f"{field} does not reference an existing record"

    try:
        quantity = int(row["qty"])
    except ValueError:
        return False, "qty must be an integer"
    if quantity <= 0:
        return False, "qty must be positive"

    try:
        datetime.fromisoformat(row["ordered_at"])
    except ValueError:
        return False, "ordered_at must be an ISO-8601 timestamp"
    if row["status"] not in STATUSES:
        return False, "status is not supported"
    return True, ""


def load(path):
    """Insert valid rows and write rejected rows with their reasons."""
    rows = list(read_rows(path))
    rejected = []
    inserted = 0
    dsn = os.environ.get("DB_DSN", DB_DSN)

    with psycopg.connect(dsn) as connection:
        with connection.cursor() as cursor:
            for row in rows:
                ok, reason = validate(row)
                if not ok:
                    rejected.append({
                        **{field: row.get(field, "") for field in FIELDS},
                        "reason": reason,
                    })
                    continue
                try:
                    cursor.execute(
                        """
                        INSERT INTO orders (customer_id, drink_id, store_id, qty, ordered_at, status)
                        VALUES (%s, %s, %s, %s, %s, %s)
                        """,
                        (
                            int(row["customer_id"]), int(row["drink_id"]), int(row["store_id"]),
                            int(row["qty"]), row["ordered_at"], row["status"],
                        ),
                    )
                    inserted += 1
                except psycopg.Error as error:
                    connection.rollback()
                    rejected.append({**row, "reason": str(error).splitlines()[0]})

    output = Path("evidence/rejected.csv")
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", newline="", encoding="utf-8") as target:
        writer = csv.DictWriter(target, fieldnames=FIELDS + ["reason"])
        writer.writeheader()
        writer.writerows(rejected)

    print(f"read {len(rows)} rows")
    print(f"inserted {inserted}")
    print(f"rejected {len(rejected)} -> {output}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("usage: python ingest/loader.py <csv-path>", file=sys.stderr)
        sys.exit(2)
    load(Path(sys.argv[1]))

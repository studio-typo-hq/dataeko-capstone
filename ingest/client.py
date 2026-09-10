"""
Client for fetching all orders from the Orders API.

The client handles pagination, authentication, rate limiting, and retries.
"""

import os
import time

import requests


API_URL = os.environ.get("API_URL", "http://127.0.0.1:8000")
API_KEY = os.environ.get("API_KEY")
PAGE_SIZE = 100
TIMEOUT = 10


def fetch_all_orders():
    """Fetch every order from the API and return them as a list."""
    if not API_KEY:
        raise RuntimeError("API_KEY environment variable is required")

    headers = {
        "Authorization": f"Bearer {API_KEY}",
    }

    orders = []
    page = 1

    while True:
        response = requests.get(
            f"{API_URL}/orders",
            params={
                "page": page,
                "per_page": PAGE_SIZE,
            },
            headers=headers,
            timeout=TIMEOUT,
        )

        if response.status_code == 429:
            retry_after = response.headers.get("Retry-After", "1")
            try:
                wait_seconds = max(1, int(retry_after))
            except ValueError:
                wait_seconds = 1

            print(f"Rate limited; waiting {wait_seconds} seconds...")
            time.sleep(wait_seconds)
            continue

        response.raise_for_status()

        data = response.json()
        results = data.get("results", [])
        orders.extend(results)

        if len(results) == 0 or len(orders) >= data["total"]:
            break

        page += 1

    print(f"total orders collected: {len(orders)}")
    return orders


if __name__ == "__main__":
    fetch_all_orders()

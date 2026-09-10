"""
Client for the DATAEKO orders API.

Pages through all orders and retries when the API returns HTTP 429.
"""

import os
import time

import requests


def fetch_all_orders(
    base_url="http://localhost:8000",
    per_page=100,
    max_orders=None,
):
    """Fetch every order from the API (or up to max_orders if specified)."""

    api_key = os.environ.get("API_KEY", "")

    headers = {
        "Authorization": f"Bearer {api_key}",
    }

    page = 1
    orders = []

    while True:
        response = requests.get(
            f"{base_url}/orders",
            params={
                "page": page,
                "per_page": per_page,
            },
            headers=headers,
            timeout=10,
        )

        if response.status_code == 429:
            retry_after = int(response.headers.get("Retry-After", "10"))
            time.sleep(retry_after)
            continue

        response.raise_for_status()

        payload = response.json()
        results = payload["results"]

        orders.extend(results)

        if (max_orders and len(orders) >= max_orders) or len(orders) >= payload["total"] or not results:
            break

        page += 1

    print(f"collected {len(orders)} orders")
    return orders


if __name__ == "__main__":
    fetch_all_orders()

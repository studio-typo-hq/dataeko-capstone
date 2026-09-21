"""Small resilient client for paging through the orders API."""
import os
import time

import requests


def collect(base_url, key, timeout=10):
    page = 1
    orders = []
    while True:
        response = requests.get(
            f"{base_url.rstrip('/')}/orders",
            params={"page": page, "per_page": 100},
            headers={"Authorization": f"Bearer {key}"},
            timeout=timeout,
        )
        if response.status_code == 429:
            time.sleep(int(response.headers.get("Retry-After", "1")))
            continue
        response.raise_for_status()
        payload = response.json()
        orders.extend(payload["results"])
        if len(orders) >= payload["total"] or not payload["results"]:
            break
        page += 1
    print(f"collected {len(orders)} orders")
    return orders


if __name__ == "__main__":
    collect(os.environ.get("API", "http://localhost:8000"), os.environ["API_KEY"])
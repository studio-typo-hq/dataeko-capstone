import os
import time

import requests


BASE_URL = os.environ.get("API_URL", "http://127.0.0.1:8001")
API_KEY = os.environ.get("API_KEY", "")


def fetch_all_orders():
    """Fetch every order from the API, retrying when rate limited."""
    page = 1
    per_page = 100
    orders = []

    while True:
        response = requests.get(
            f"{BASE_URL}/orders",
            params={"page": page, "per_page": per_page},
            headers={"Authorization": f"Bearer {API_KEY}"},
            timeout=10,
        )

        if response.status_code == 429:
            retry_after = int(response.headers.get("Retry-After", "1"))
            time.sleep(retry_after)
            continue

        response.raise_for_status()

        data = response.json()
        orders.extend(data["results"])

        if page * data["per_page"] >= data["total"]:
            break

        page += 1

    print(f"collected {len(orders)} orders")
    return orders


if __name__ == "__main__":
    fetch_all_orders()

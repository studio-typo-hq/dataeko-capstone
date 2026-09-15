import os
import time

import requests


def fetch_all_orders(base_url, api_key, per_page=100):
    page = 1
    orders = []

    headers = {
        "Authorization": f"Bearer {api_key}"
    }

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
            retry_after = int(
                response.headers.get("Retry-After", "1")
            )
            time.sleep(retry_after)
            continue

        response.raise_for_status()

        payload = response.json()
        results = payload.get("results", [])

        orders.extend(results)

        if len(results) == 0:
            break

        if len(orders) >= payload["total"]:
            break

        page += 1

    print(f"collected={len(orders)}")
    return orders


if __name__ == "__main__":
    base_url = os.environ.get(
        "API_URL",
        "http://127.0.0.1:8000",
    )
    api_key = os.environ.get("API_KEY", "")

    fetch_all_orders(base_url, api_key)

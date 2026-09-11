import os
import time

import requests


BASE_URL = "http://127.0.0.1:8001"
API_KEY = os.environ.get("API_KEY", "dataeko-capstone-key")
TIMEOUT = 10


def fetch_all_orders():
    orders = []
    page = 1
    per_page = 100

    headers = {
        "Authorization": f"Bearer {API_KEY}"
    }

    while True:
        response = requests.get(
            f"{BASE_URL}/orders",
            headers=headers,
            params={
                "page": page,
                "per_page": per_page,
            },
            timeout=TIMEOUT,
        )

        if response.status_code == 429:
            retry_after = int(response.headers.get("Retry-After", "1"))
            print(f"Rate limited. Waiting {retry_after} seconds...")
            time.sleep(retry_after)
            continue

        response.raise_for_status()

        data = response.json()
        results = data["results"]

        orders.extend(results)

        print(
            f"Page {page}: collected {len(results)} orders "
            f"(total collected: {len(orders)})"
        )

        if not results or len(orders) >= data["total"]:
            break

        page += 1

    return orders


if __name__ == "__main__":
    orders = fetch_all_orders()
    print(f"Total orders collected: {len(orders)}")

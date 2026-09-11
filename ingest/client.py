import os
import time

import requests


def fetch_all_orders(base_url, api_key, per_page=100):
    page = 1
    all_orders = []

    while True:
        response = requests.get(
            f"{base_url}/orders",
            headers={"Authorization": f"Bearer {api_key}"},
            params={"page": page, "per_page": per_page},
            timeout=10,
        )

        if response.status_code == 429:
            retry_after = int(response.headers.get("Retry-After", "1"))
            print(f"Rate limited. Waiting {retry_after} seconds...")
            time.sleep(retry_after)
            continue

        response.raise_for_status()

        data = response.json()
        results = data["results"]

        all_orders.extend(results)

        print(
            f"Fetched page {page}: "
            f"{len(results)} orders "
            f"(total collected: {len(all_orders)}/{data['total']})"
        )

        if len(all_orders) >= data["total"] or not results:
            break

        page += 1

    print(f"Collected {len(all_orders)} orders")
    return all_orders


if __name__ == "__main__":
    base_url = os.environ.get(
        "API_URL",
        "http://localhost:8000",
    )

    api_key = os.environ.get("API_KEY")

    if not api_key:
        raise SystemExit("API_KEY environment variable is required")

    fetch_all_orders(base_url, api_key)

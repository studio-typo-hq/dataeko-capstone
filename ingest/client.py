"""
API client for fetching orders from the Capstone API.
Pages through all orders, respects 429 Retry-After, and prints total orders collected.
"""
import os
import sys
import time
import requests

API_URL = os.environ.get("API_URL", "http://localhost:8000")
API_KEY = os.environ.get("API_KEY", "dataeko-capstone-test-key")
TIMEOUT = 10


def fetch_all_orders(base_url: str = API_URL, api_key: str = API_KEY) -> list:
    headers = {"Authorization": f"Bearer {api_key}"}
    page = 1
    per_page = 100
    all_orders = []
    total_expected = None

    while True:
        url = f"{base_url}/orders?page={page}&per_page={per_page}"
        try:
            resp = requests.get(url, headers=headers, timeout=TIMEOUT)
        except requests.RequestException as e:
            print(f"Network error on page {page}: {e}, retrying in 2s...", file=sys.stderr)
            time.sleep(2)
            continue

        if resp.status_code == 429:
            retry_after = int(resp.headers.get("Retry-After", "1"))
            print(f"Rate limited (429). Waiting {retry_after} seconds...", file=sys.stderr)
            time.sleep(retry_after)
            continue

        if resp.status_code != 200:
            print(f"Error fetching page {page}: {resp.status_code} {resp.text}", file=sys.stderr)
            resp.raise_for_status()

        data = resp.json()
        orders_batch = data.get("results") or data.get("orders") or []
        all_orders.extend(orders_batch)

        if total_expected is None:
            total_expected = data.get("total", 0)

        if len(orders_batch) == 0 or len(all_orders) >= total_expected:
            break

        page += 1

    return all_orders


def main():
    orders = fetch_all_orders()
    print(f"Collected total {len(orders)} orders")


if __name__ == "__main__":
    main()

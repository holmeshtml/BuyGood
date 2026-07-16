"""
Extract all event streams from the BuyGood data generator API.
Seeds random data into Lakehouse.raw.orders, Lakehouse.raw.page_views, and Lakehouse.raw.cart_adds.
Designed to run in a Fabric notebook with a Lakehouse attached.
"""

import requests
import pandas as pd

# --- Config ---
API_BASE_URL = "https://buygood-production.up.railway.app"
DAYS = 1
BACKFILL_SPIKE = False

STREAMS = [
    {"endpoint": "orders", "table": "Lakehouse.raw.orders", "flatten_cols": ["line_items", "status_history"]},
    {"endpoint": "page_views", "table": "Lakehouse.raw.page_views", "flatten_cols": []},
    {"endpoint": "cart_adds", "table": "Lakehouse.raw.cart_adds", "flatten_cols": []},
]

# --- Extract & Load each stream separately ---
for stream in STREAMS:
    response = requests.post(
        f"{API_BASE_URL}/generate/{stream['endpoint']}",
        params={"days": DAYS, "backfill_spike": BACKFILL_SPIKE},
    )
    response.raise_for_status()
    data = response.json()

    df = pd.json_normalize(data["events"])

    # Flatten nested columns to strings for tabular storage
    for col in stream["flatten_cols"]:
        if col in df.columns:
            df[col] = df[col].apply(lambda x: str(x) if x else None)

    spark.createDataFrame(df).write.mode("append").saveAsTable(stream["table"])
    print(f"✓ {stream['table']}: {data['count']} rows (seed: {data['seed']})")

print("\nDone")

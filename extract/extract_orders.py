"""
Extract all event streams from the BuyGood data generator API.
Seeds random data into raw.orders, raw.page_views, and raw.cart_adds.
Designed to run in a Fabric notebook with a Lakehouse attached.
"""

import requests
import pandas as pd

# --- Config ---
API_BASE_URL = "https://buygood-production.up.railway.app"
DAYS = 1
BACKFILL_SPIKE = False

# --- Extract all streams ---
response = requests.post(
    f"{API_BASE_URL}/generate/all",
    params={"days": DAYS, "backfill_spike": BACKFILL_SPIKE},
)
response.raise_for_status()
data = response.json()

# --- Orders ---
df_orders = pd.json_normalize(data["orders"]["events"])
for col in ["line_items", "status_history"]:
    if col in df_orders.columns:
        df_orders[col] = df_orders[col].apply(lambda x: str(x) if x else None)

spark.createDataFrame(df_orders).write.mode("append").saveAsTable("raw.orders")
print(f"✓ raw.orders: {data['orders']['count']} rows")

# --- Page Views ---
df_page_views = pd.json_normalize(data["page_views"]["events"])
spark.createDataFrame(df_page_views).write.mode("append").saveAsTable("raw.page_views")
print(f"✓ raw.page_views: {data['page_views']['count']} rows")

# --- Cart Adds ---
df_cart_adds = pd.json_normalize(data["cart_adds"]["events"])
spark.createDataFrame(df_cart_adds).write.mode("append").saveAsTable("raw.cart_adds")
print(f"✓ raw.cart_adds: {data['cart_adds']['count']} rows")

print(f"\nDone | seed: {data['seed']} | gen_time: {data['generation_time_ms']}ms")

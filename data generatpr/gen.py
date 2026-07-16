import argparse
import json
import random
from datetime import UTC, datetime, timedelta
from pathlib import Path
from collections import defaultdict
from uuid import uuid4

LANDING_DIR = Path("landing")
SOURCE_NAME = "goodbuy_ecommerce"
MAX_EVENTS_PER_FILE = 6000


from faker import Faker

SEED = 42
ORDERS_PER_DAY_MIN = 8
ORDERS_PER_DAY_MAX = 25
REFUND_RATE = 0.08
PAGE_SESSIONS_PER_DAY_MIN = 250
PAGE_SESSIONS_PER_DAY_MAX = 650
SESSION_PAGE_VIEWS_MIN = 1
SESSION_PAGE_VIEWS_MAX = 10
LOGGED_IN_SESSION_RATE = 0.42
CART_ADDS_PER_SESSION_MIN = 0
CART_ADDS_PER_SESSION_MAX = 3
LATE_PROFILE_DEFAULT = {
     "on_time": 0.86,
     "late_minutes": 0.10,
     "late_hours": 0.03,
     "late_day": 0.01,
}
LATE_PROFILE_BACKFILL = {
     "on_time": 0.55,
     "late_minutes": 0.25,
     "late_hours": 0.15,
     "late_day": 0.05,
}

CATALOG = [
     {"product_id": "P-1001", "name": "Laptop", "unit_price": 1099.0},
     {"product_id": "P-1002", "name": "Smartphone", "unit_price": 799.0},
     {"product_id": "P-1003", "name": "Tablet", "unit_price": 499.0},
     {"product_id": "P-1004", "name": "Headphones", "unit_price": 149.0},
     {"product_id": "P-1005", "name": "Camera", "unit_price": 899.0},
     {"product_id": "P-1006", "name": "Smartwatch", "unit_price": 299.0},
     {"product_id": "P-1007", "name": "Printer", "unit_price": 229.0},
     {"product_id": "P-1008", "name": "Monitor", "unit_price": 349.0},
     {"product_id": "P-1009", "name": "Keyboard", "unit_price": 89.0},
     {"product_id": "P-1010", "name": "Mouse", "unit_price": 59.0},
]

PAGE_PATHS = [
     "/",
     "/products",
     "/products/laptop",
     "/products/smartphone",
     "/products/tablet",
     "/search",
     "/cart",
     "/checkout",
     "/deals",
     "/support",
]

REFERRERS = [
     "direct",
     "google",
     "instagram",
     "email",
     "youtube",
     "affiliate",
]

DEVICES = ["mobile", "desktop", "tablet"]

def _chunked(items, size):
    # Split a large in-memory list into fixed-size batches.
    # Example: 12,500 events with size=6,000 -> 3 chunks (6000, 6000, 500).
    # This keeps each landing file a manageable size for downstream jobs.
    for i in range(0, len(items), size):
        yield items[i:i + size]

def write_partitioned_events(events: list[dict],event_type: str, landing_dir: Path = LANDING_DIR,source_name: str = SOURCE_NAME, max_events_per_file: int = MAX_EVENTS_PER_FILE) -> list[Path]:
     # This function is the landing-zone writer.
     # Input: an in-memory list of event dictionaries for one stream (orders/page_views/cart_adds).
     # Output: raw files partitioned by ingestion date, returning all created file paths.
     #
     # Why ingestion date partitioning?
     # - It matches how data pipelines process "new arrivals" incrementally.
     # - It naturally supports late events and backfills without rewriting old files.
     # - Downstream jobs can read only the newest partitions for efficiency.
     # Group all generated events by ingested date, not event date.
     # This matches common lakehouse ingestion patterns where arrival time drives
     # partition layout and incremental processing.
     grouped = defaultdict(list)
     for event in events:
          ingested_date = datetime.fromisoformat(event["ingested_time"]).date()
          grouped[ingested_date].append(event)
     
     written_files = []
     # One run_id ties files together so you can trace "which generator run"
     # created a specific batch in the landing zone.
     run_id = uuid4().hex[:8]

     for ingested_date, events_on_date in grouped.items():
          # Partition layout convention:
          # landing/<source>/event_type=<type>/ingested_date=<YYYY-MM-DD>/
          #
          # Using ingested_date here is important for late-arriving data:
          # older event_time values can still land in today's partition naturally.
          partition_dir = landing_dir / f"{source_name}/event_type={event_type}/ingested_date={ingested_date}"
          partition_dir.mkdir(parents=True, exist_ok=True)

          for chunk in _chunked(events_on_date, max_events_per_file):
               # Each chunk becomes one file so downstream systems can process
               # incrementally and avoid loading a giant single object.
               #
               # NOTE: This currently writes JSON arrays (.json). If you want
               # strict line-delimited raw format, switch to .jsonl and write
               # one json.dumps(record) per line.
               file_path = partition_dir / f"{run_id}_{uuid4().hex[:8]}.json"
               with file_path.open("w") as f:
                    json.dump(chunk, f, default=str)
               written_files.append(file_path)  

     # Return created paths so caller can log/validate exactly what landed.
     return written_files





          
def _generate_session_contexts(
     days: int,
     seed: int,
     customers: list[dict],
) -> list[dict]:
     rng = random.Random(seed + 99)
     now = datetime.now(UTC).replace(microsecond=0)
     start_date = now - timedelta(days=days)
     sessions: list[dict] = []
     session_counter = 1

     for day_offset in range(days):
          day_base = start_date + timedelta(days=day_offset)
          day_sessions = rng.randint(PAGE_SESSIONS_PER_DAY_MIN, PAGE_SESSIONS_PER_DAY_MAX)

          for _ in range(day_sessions):
               session_start = day_base + timedelta(
                    hours=rng.randint(0, 23),
                    minutes=rng.randint(0, 59),
                    seconds=rng.randint(0, 59),
               )
               is_logged_in = rng.random() < LOGGED_IN_SESSION_RATE
               customer_id = rng.choice(customers)["customer_id"] if is_logged_in else None

               sessions.append(
                    {
                         "session_id": f"S-{session_counter:09d}",
                         "session_start": session_start,
                         "customer_id": customer_id,
                         "is_logged_in": is_logged_in,
                         "device": rng.choice(DEVICES),
                         "referrer": rng.choice(REFERRERS),
                    }
               )
               session_counter += 1

     return sessions


def _build_customer_pool(fake: Faker, count: int = 200) -> list[dict]:
     customers = []
     for idx in range(1, count + 1):
          customers.append(
               {
                    "customer_id": f"C-{idx:05d}",
                    "full_name": fake.name(),
                    "email": fake.email(),
               }
          )
     return customers


def _create_line_items(rng: random.Random) -> list[dict]:
     item_count = rng.randint(1, 4)
     sampled_products = rng.sample(CATALOG, k=item_count)
     line_items = []

     for item in sampled_products:
          quantity = rng.randint(1, 3)
          line_total = round(item["unit_price"] * quantity, 2)
          line_items.append(
               {
                    "product_id": item["product_id"],
                    "product_name": item["name"],
                    "unit_price": item["unit_price"],
                    "quantity": quantity,
                    "line_total": line_total,
               }
          )

     return line_items


def _sample_ingested_time(
     event_time: datetime,
     rng: random.Random,
     backfill_spike: bool = False,
) -> tuple[datetime, str]:
     profile = LATE_PROFILE_BACKFILL if backfill_spike else LATE_PROFILE_DEFAULT
     draw = rng.random()

     if draw < profile["on_time"]:
          delay_seconds = rng.randint(5, 180)
          bucket = "on_time"
     elif draw < profile["on_time"] + profile["late_minutes"]:
          delay_seconds = rng.randint(5 * 60, 45 * 60)
          bucket = "late_minutes"
     elif draw < profile["on_time"] + profile["late_minutes"] + profile["late_hours"]:
          delay_seconds = rng.randint(60 * 60, 12 * 60 * 60)
          bucket = "late_hours"
     else:
          delay_seconds = rng.randint(24 * 60 * 60, 48 * 60 * 60)
          bucket = "late_day"

     return event_time + timedelta(seconds=delay_seconds), bucket


def _build_status_history(placed_at: datetime, rng: random.Random) -> tuple[str, list[dict]]:
     paid_at = placed_at + timedelta(minutes=rng.randint(1, 45))
     shipped_at = paid_at + timedelta(hours=rng.randint(2, 72))

     history = [
          {"status": "placed", "status_at": placed_at.isoformat()},
          {"status": "paid", "status_at": paid_at.isoformat()},
          {"status": "shipped", "status_at": shipped_at.isoformat()},
     ]

     if rng.random() < REFUND_RATE:
          refunded_at = shipped_at + timedelta(days=rng.randint(1, 14))
          history.append({"status": "refunded", "status_at": refunded_at.isoformat()})
          return "refunded", history

     return "shipped", history


def generate_orders(
     days: int = 14,
     output_file: str = "landing/orders.jsonl",
     seed: int = SEED,
     backfill_spike: bool = False,
) -> list[dict]:
     fake = Faker()
     fake.seed_instance(seed)
     rng = random.Random(seed)

     customers = _build_customer_pool(fake)
     now = datetime.now(UTC).replace(microsecond=0)
     start_date = now - timedelta(days=days)
     orders: list[dict] = []

     order_counter = 1
     for day_offset in range(days):
          day_base = start_date + timedelta(days=day_offset)
          day_order_count = rng.randint(ORDERS_PER_DAY_MIN, ORDERS_PER_DAY_MAX)

          for _ in range(day_order_count):
               customer = rng.choice(customers)
               placed_at = day_base + timedelta(
                    hours=rng.randint(8, 22),
                    minutes=rng.randint(0, 59),
                    seconds=rng.randint(0, 59),
               )

               line_items = _create_line_items(rng)
               order_total = round(sum(item["line_total"] for item in line_items), 2)
               current_status, status_history = _build_status_history(placed_at, rng)
               ingested_at, late_bucket = _sample_ingested_time(placed_at, rng, backfill_spike=backfill_spike)

               orders.append(
                    {
                         "order_id": f"O-{order_counter:08d}",
                         "customer_id": customer["customer_id"],
                         "event_time": placed_at.isoformat(),
                         "placed_at": placed_at.isoformat(),
                         "ingested_time": ingested_at.isoformat(),
                         "late_bucket": late_bucket,
                         "ingestion_delay_seconds": int((ingested_at - placed_at).total_seconds()),
                         "current_status": current_status,
                         "status_history": status_history,
                         "line_items": line_items,
                         "order_total": order_total,
                         "currency": "USD",
                    }
               )
               order_counter += 1

     output_path = Path(output_file)
     output_path.parent.mkdir(parents=True, exist_ok=True)
     with output_path.open("w", encoding="utf-8") as file_handle:
          for order in orders:
               file_handle.write(json.dumps(order) + "\n")

     return orders


def generate_page_views(
     days: int = 14,
     output_file: str = "landing/page_views.jsonl",
     seed: int = SEED,
     backfill_spike: bool = False,
) -> list[dict]:
     fake = Faker()
     fake.seed_instance(seed)
     rng = random.Random(seed + 1)

     customers = _build_customer_pool(fake)
     sessions = _generate_session_contexts(days=days, seed=seed, customers=customers)
     page_views: list[dict] = []

     view_counter = 1

     for session in sessions:
          views_in_session = rng.randint(SESSION_PAGE_VIEWS_MIN, SESSION_PAGE_VIEWS_MAX)

          for view_index in range(views_in_session):
               view_time = session["session_start"] + timedelta(seconds=rng.randint(view_index * 7, view_index * 90 + 10))
               ingested_at, late_bucket = _sample_ingested_time(view_time, rng, backfill_spike=backfill_spike)
               page_views.append(
                    {
                         "page_view_id": f"PV-{view_counter:012d}",
                         "session_id": session["session_id"],
                         "customer_id": session["customer_id"],
                         "event_time": view_time.isoformat(),
                         "ingested_time": ingested_at.isoformat(),
                         "late_bucket": late_bucket,
                         "ingestion_delay_seconds": int((ingested_at - view_time).total_seconds()),
                         "page_path": rng.choice(PAGE_PATHS),
                         "referrer": session["referrer"],
                         "device": session["device"],
                         "is_logged_in": session["is_logged_in"],
                    }
               )
               view_counter += 1

     output_path = Path(output_file)
     output_path.parent.mkdir(parents=True, exist_ok=True)
     with output_path.open("w", encoding="utf-8") as file_handle:
          for event in page_views:
               file_handle.write(json.dumps(event) + "\n")

     return page_views


def generate_cart_adds(
     days: int = 14,
     output_file: str = "landing/cart_adds.jsonl",
     seed: int = SEED,
     backfill_spike: bool = False,
) -> list[dict]:
     fake = Faker()
     fake.seed_instance(seed)
     rng = random.Random(seed + 2)

     customers = _build_customer_pool(fake)
     sessions = _generate_session_contexts(days=days, seed=seed, customers=customers)
     cart_adds: list[dict] = []

     cart_add_counter = 1
     for session in sessions:
          adds_in_session = rng.randint(CART_ADDS_PER_SESSION_MIN, CART_ADDS_PER_SESSION_MAX)
          for _ in range(adds_in_session):
               product = rng.choice(CATALOG)
               quantity = rng.randint(1, 3)
               event_time = session["session_start"] + timedelta(seconds=rng.randint(20, 600))
               ingested_at, late_bucket = _sample_ingested_time(event_time, rng, backfill_spike=backfill_spike)

               cart_adds.append(
                    {
                         "cart_add_id": f"CA-{cart_add_counter:012d}",
                         "session_id": session["session_id"],
                         "customer_id": session["customer_id"],
                         "event_time": event_time.isoformat(),
                         "ingested_time": ingested_at.isoformat(),
                         "late_bucket": late_bucket,
                         "ingestion_delay_seconds": int((ingested_at - event_time).total_seconds()),
                         "product_id": product["product_id"],
                         "product_name": product["name"],
                         "unit_price": product["unit_price"],
                         "quantity": quantity,
                         "cart_add_value": round(product["unit_price"] * quantity, 2),
                    }
               )
               cart_add_counter += 1

     output_path = Path(output_file)
     output_path.parent.mkdir(parents=True, exist_ok=True)
     with output_path.open("w", encoding="utf-8") as file_handle:
          for event in cart_adds:
               file_handle.write(json.dumps(event) + "\n")

     return cart_adds


if __name__ == "__main__":
     # Main flow overview:
     # 1) Parse CLI flags for reproducibility (days/seed) and lateness simulation.
     # 2) Generate each event stream in memory with event_time + ingested_time.
     # 3) Write each stream into partitioned landing files by ingested_date.
     # 4) Print counts so you can quickly verify what was produced.
     #
     # This separation is intentional: generation creates records, writer decides storage layout.
     # That makes it easy later to swap local files for S3/MinIO without changing event logic.

     # CLI flags let you reproduce the same dataset and optionally amplify
     # late-arrival behavior for backfill simulations.
    parser = argparse.ArgumentParser(description="Generate fake ecommerce event streams.")
    parser.add_argument("--days", type=int, default=14, help="Number of historical days to generate.")
    parser.add_argument("--seed", type=int, default=SEED, help="Random seed for deterministic output.")
    parser.add_argument(
        "--backfill-spike",
        action="store_true",
        help="Increase late-arrival rates to simulate backfill-heavy batches.",
    )
    args = parser.parse_args()

     # Step 1: generate in-memory event lists for each stream.
     # Each record already contains event_time (business timestamp)
     # and ingested_time (arrival timestamp).
    generated_orders = generate_orders(days=args.days, seed=args.seed, backfill_spike=args.backfill_spike)
    generated_page_views = generate_page_views(days=args.days, seed=args.seed, backfill_spike=args.backfill_spike)
    generated_cart_adds = generate_cart_adds(days=args.days, seed=args.seed, backfill_spike=args.backfill_spike)

     # Step 2: land each stream into partitioned raw files.
     # This is the canonical landing-zone write path used by downstream consumers.
    order_files = write_partitioned_events(generated_orders, "orders")
    pv_files = write_partitioned_events(generated_page_views, "page_views")
    ca_files = write_partitioned_events(generated_cart_adds, "cart_adds")

     # Step 3: print summary so you can quickly verify file counts per stream.
     # If these are zero, generation or partitioning likely failed upstream.
    print(f"Wrote {len(order_files)} order files")
    print(f"Wrote {len(pv_files)} page view files")
    print(f"Wrote {len(ca_files)} cart add files")
    print(f"Backfill spike mode: {args.backfill_spike}")
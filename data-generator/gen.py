import argparse
import json
import random
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

from faker import Faker

LANDING_DIR = Path("landing")
SOURCE_NAME = "goodbuy_ecommerce"
MAX_EVENTS_PER_FILE = 6000

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

CATALOG = [
    {"product_id": "P-1001", "name": "Laptop", "category": "Electronics", "unit_price": 1099.99},
    {"product_id": "P-1002", "name": "Smartphone", "category": "Electronics", "unit_price": 799.49},
    {"product_id": "P-1003", "name": "Tablet", "category": "Electronics", "unit_price": 499.95},
    {"product_id": "P-1004", "name": "Headphones", "category": "Accessories", "unit_price": 149.89},
    {"product_id": "P-1005", "name": "Camera", "category": "Electronics", "unit_price": 899.79},
    {"product_id": "P-1006", "name": "Smartwatch", "category": "Accessories", "unit_price": 299.59},
    {"product_id": "P-1007", "name": "Printer", "category": "Office", "unit_price": 229.47},
    {"product_id": "P-1008", "name": "Monitor", "category": "Electronics", "unit_price": 349.29},
    {"product_id": "P-1009", "name": "Keyboard", "category": "Accessories", "unit_price": 89.95},
    {"product_id": "P-1010", "name": "Mouse", "category": "Accessories", "unit_price": 59.49},
]

PAGE_PATHS = ["/", "/products", "/products/laptop", "/products/smartphone",
              "/products/tablet", "/search", "/cart", "/checkout", "/deals", "/support"]
REFERRERS = ["direct", "google", "instagram", "email", "youtube", "affiliate"]
DEVICES = ["mobile", "desktop", "tablet"]
PAYMENT_METHODS = ["credit_card", "debit_card", "paypal", "apple_pay", "google_pay"]


# ---------------------------------------------------------------------------
# Generators
# ---------------------------------------------------------------------------

def _build_customer_pool(fake: Faker, count: int = 200) -> list[dict]:
    customers = []
    for idx in range(1, count + 1):
        customers.append({
            "customer_id": f"C-{idx:05d}",
            "full_name": fake.name(),
            "email": fake.email(),
            "phone": fake.phone_number(),
            "address": fake.address().replace("\n", ", "),
            "created_at": fake.date_time_between(start_date="-2y", end_date="-30d", tzinfo=UTC).isoformat(),
        })
    return customers


def _build_products() -> list[dict]:
    return [
        {
            "product_id": p["product_id"],
            "name": p["name"],
            "category": p["category"],
            "created_at": "2024-01-01T00:00:00+00:00",
        }
        for p in CATALOG
    ]


def _build_product_prices(rng: random.Random) -> list[dict]:
    """Generate price history for each product. Current price + one older price."""
    prices = []
    for p in CATALOG:
        prices.append({
            "product_id": p["product_id"],
            "price": p["unit_price"],
            "currency": "USD",
            "valid_from": "2025-01-01T00:00:00+00:00",
            "valid_to": None,
        })
        old_price = round(p["unit_price"] * rng.uniform(0.85, 1.15), 2)
        prices.append({
            "product_id": p["product_id"],
            "price": old_price,
            "currency": "USD",
            "valid_from": "2024-01-01T00:00:00+00:00",
            "valid_to": "2024-12-31T23:59:59+00:00",
        })
    return prices


def generate_orders(
    days: int = 14,
    seed: int = SEED,
) -> tuple[list[dict], list[dict], list[dict]]:
    """Generate orders, order_items, and payments tables."""
    fake = Faker()
    fake.seed_instance(seed)
    rng = random.Random(seed)

    customers = _build_customer_pool(fake)
    now = datetime.now(UTC).replace(microsecond=0)
    start_date = now - timedelta(days=days)

    orders = []
    order_items = []
    payments = []

    order_counter = 1
    item_counter = 1
    payment_counter = 1

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

            order_id = f"O-{order_counter:08d}"

            num_items = rng.randint(1, 4)
            sampled_products = rng.sample(CATALOG, k=num_items)
            order_total = 0.0

            for product in sampled_products:
                quantity = rng.randint(1, 3)
                line_total = round(product["unit_price"] * quantity, 2)
                order_total += line_total

                order_items.append({
                    "order_item_id": f"OI-{item_counter:010d}",
                    "order_id": order_id,
                    "product_id": product["product_id"],
                    "quantity": quantity,
                    "unit_price": product["unit_price"],
                    "line_total": line_total,
                })
                item_counter += 1

            order_total = round(order_total, 2)

            is_refunded = rng.random() < REFUND_RATE
            status = "refunded" if is_refunded else "shipped"

            orders.append({
                "order_id": order_id,
                "customer_id": customer["customer_id"],
                "status": status,
                "order_total": order_total,
                "currency": "USD",
                "placed_at": placed_at.isoformat(),
                "updated_at": (placed_at + timedelta(hours=rng.randint(2, 72))).isoformat(),
            })

            paid_at = placed_at + timedelta(minutes=rng.randint(1, 45))
            payments.append({
                "payment_id": f"PAY-{payment_counter:010d}",
                "order_id": order_id,
                "amount": order_total,
                "currency": "USD",
                "method": rng.choice(PAYMENT_METHODS),
                "status": "refunded" if is_refunded else "completed",
                "paid_at": paid_at.isoformat(),
            })
            payment_counter += 1
            order_counter += 1

    return orders, order_items, payments


def generate_events(
    days: int = 14,
    seed: int = SEED,
) -> list[dict]:
    """Generate a unified events table (page_view, cart_add event types)."""
    fake = Faker()
    fake.seed_instance(seed)
    rng = random.Random(seed + 1)

    customers = _build_customer_pool(fake)
    now = datetime.now(UTC).replace(microsecond=0)
    start_date = now - timedelta(days=days)

    events = []
    event_counter = 1
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
            session_id = f"S-{session_counter:09d}"
            is_logged_in = rng.random() < LOGGED_IN_SESSION_RATE
            customer_id = rng.choice(customers)["customer_id"] if is_logged_in else None
            device = rng.choice(DEVICES)
            referrer = rng.choice(REFERRERS)

            views_in_session = rng.randint(SESSION_PAGE_VIEWS_MIN, SESSION_PAGE_VIEWS_MAX)
            for view_index in range(views_in_session):
                event_time = session_start + timedelta(seconds=rng.randint(view_index * 7, view_index * 90 + 10))
                events.append({
                    "event_id": f"E-{event_counter:012d}",
                    "event_type": "page_view",
                    "session_id": session_id,
                    "customer_id": customer_id,
                    "event_time": event_time.isoformat(),
                    "device": device,
                    "referrer": referrer,
                    "page_path": rng.choice(PAGE_PATHS),
                    "product_id": None,
                    "quantity": None,
                })
                event_counter += 1

            adds_in_session = rng.randint(CART_ADDS_PER_SESSION_MIN, CART_ADDS_PER_SESSION_MAX)
            for _ in range(adds_in_session):
                product = rng.choice(CATALOG)
                quantity = rng.randint(1, 3)
                event_time = session_start + timedelta(seconds=rng.randint(20, 600))
                events.append({
                    "event_id": f"E-{event_counter:012d}",
                    "event_type": "cart_add",
                    "session_id": session_id,
                    "customer_id": customer_id,
                    "event_time": event_time.isoformat(),
                    "device": device,
                    "referrer": referrer,
                    "page_path": None,
                    "product_id": product["product_id"],
                    "quantity": quantity,
                })
                event_counter += 1

            session_counter += 1

    return events


# ---------------------------------------------------------------------------
# Writers
# ---------------------------------------------------------------------------

def _chunked(items, size):
    for i in range(0, len(items), size):
        yield items[i:i + size]


def write_partitioned_json(records: list[dict], stream_name: str) -> list[Path]:
    """Write records as partitioned JSON files in the landing zone."""
    run_id = uuid4().hex[:8]
    partition_dir = LANDING_DIR / f"{SOURCE_NAME}/{stream_name}"
    partition_dir.mkdir(parents=True, exist_ok=True)

    written_files = []
    for chunk in _chunked(records, MAX_EVENTS_PER_FILE):
        file_path = partition_dir / f"{run_id}_{uuid4().hex[:8]}.json"
        with file_path.open("w") as f:
            json.dump(chunk, f, default=str)
        written_files.append(file_path)

    return written_files


def write_to_postgres(
    customers: list[dict],
    products: list[dict],
    product_prices: list[dict],
    orders: list[dict],
    order_items: list[dict],
    payments: list[dict],
    events: list[dict],
    database_url: str,
) -> None:
    """Write all generated data into a Postgres database.

    Expects DATABASE_URL like: postgres://user:pass@host:5432/dbname
    Drops and recreates all tables on each run (idempotent seed).
    """
    import psycopg2

    con = psycopg2.connect(database_url)
    cur = con.cursor()

    # Drop tables (reverse dependency order)
    cur.execute("DROP TABLE IF EXISTS events CASCADE")
    cur.execute("DROP TABLE IF EXISTS payments CASCADE")
    cur.execute("DROP TABLE IF EXISTS order_items CASCADE")
    cur.execute("DROP TABLE IF EXISTS orders CASCADE")
    cur.execute("DROP TABLE IF EXISTS product_prices CASCADE")
    cur.execute("DROP TABLE IF EXISTS products CASCADE")
    cur.execute("DROP TABLE IF EXISTS customers CASCADE")

    # --- customers ---
    cur.execute("""
        CREATE TABLE customers (
            customer_id VARCHAR PRIMARY KEY,
            full_name VARCHAR,
            email VARCHAR,
            phone VARCHAR,
            address VARCHAR,
            created_at TIMESTAMPTZ
        )
    """)
    for c in customers:
        cur.execute(
            "INSERT INTO customers VALUES (%s,%s,%s,%s,%s,%s)",
            (c["customer_id"], c["full_name"], c["email"], c["phone"], c["address"], c["created_at"]),
        )

    # --- products ---
    cur.execute("""
        CREATE TABLE products (
            product_id VARCHAR PRIMARY KEY,
            name VARCHAR,
            category VARCHAR,
            created_at TIMESTAMPTZ
        )
    """)
    for p in products:
        cur.execute(
            "INSERT INTO products VALUES (%s,%s,%s,%s)",
            (p["product_id"], p["name"], p["category"], p["created_at"]),
        )

    # --- product_prices ---
    cur.execute("""
        CREATE TABLE product_prices (
            product_id VARCHAR REFERENCES products(product_id),
            price NUMERIC(10,2),
            currency VARCHAR,
            valid_from TIMESTAMPTZ,
            valid_to TIMESTAMPTZ
        )
    """)
    for pp in product_prices:
        cur.execute(
            "INSERT INTO product_prices VALUES (%s,%s,%s,%s,%s)",
            (pp["product_id"], pp["price"], pp["currency"], pp["valid_from"], pp["valid_to"]),
        )

    # --- orders ---
    cur.execute("""
        CREATE TABLE orders (
            order_id VARCHAR PRIMARY KEY,
            customer_id VARCHAR REFERENCES customers(customer_id),
            status VARCHAR,
            order_total NUMERIC(10,2),
            currency VARCHAR,
            placed_at TIMESTAMPTZ,
            updated_at TIMESTAMPTZ
        )
    """)
    for o in orders:
        cur.execute(
            "INSERT INTO orders VALUES (%s,%s,%s,%s,%s,%s,%s)",
            (o["order_id"], o["customer_id"], o["status"], o["order_total"], o["currency"], o["placed_at"], o["updated_at"]),
        )

    # --- order_items ---
    cur.execute("""
        CREATE TABLE order_items (
            order_item_id VARCHAR PRIMARY KEY,
            order_id VARCHAR REFERENCES orders(order_id),
            product_id VARCHAR REFERENCES products(product_id),
            quantity INTEGER,
            unit_price NUMERIC(10,2),
            line_total NUMERIC(10,2)
        )
    """)
    for oi in order_items:
        cur.execute(
            "INSERT INTO order_items VALUES (%s,%s,%s,%s,%s,%s)",
            (oi["order_item_id"], oi["order_id"], oi["product_id"], oi["quantity"], oi["unit_price"], oi["line_total"]),
        )

    # --- payments ---
    cur.execute("""
        CREATE TABLE payments (
            payment_id VARCHAR PRIMARY KEY,
            order_id VARCHAR REFERENCES orders(order_id),
            amount NUMERIC(10,2),
            currency VARCHAR,
            method VARCHAR,
            status VARCHAR,
            paid_at TIMESTAMPTZ
        )
    """)
    for p in payments:
        cur.execute(
            "INSERT INTO payments VALUES (%s,%s,%s,%s,%s,%s,%s)",
            (p["payment_id"], p["order_id"], p["amount"], p["currency"], p["method"], p["status"], p["paid_at"]),
        )

    # --- events ---
    cur.execute("""
        CREATE TABLE events (
            event_id VARCHAR PRIMARY KEY,
            event_type VARCHAR,
            session_id VARCHAR,
            customer_id VARCHAR,
            event_time TIMESTAMPTZ,
            device VARCHAR,
            referrer VARCHAR,
            page_path VARCHAR,
            product_id VARCHAR,
            quantity INTEGER
        )
    """)
    for e in events:
        cur.execute(
            "INSERT INTO events VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
            (e["event_id"], e["event_type"], e["session_id"], e["customer_id"], e["event_time"],
             e["device"], e["referrer"], e["page_path"], e["product_id"], e["quantity"]),
        )

    con.commit()
    cur.close()
    con.close()

    print(f"Postgres: {database_url.split('@')[1] if '@' in database_url else database_url}")
    print(f"  customers:      {len(customers)}")
    print(f"  products:       {len(products)}")
    print(f"  product_prices: {len(product_prices)}")
    print(f"  orders:         {len(orders)}")
    print(f"  order_items:    {len(order_items)}")
    print(f"  payments:       {len(payments)}")
    print(f"  events:         {len(events)}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate fake ecommerce data.")
    parser.add_argument("--days", type=int, default=14, help="Number of historical days to generate.")
    parser.add_argument("--seed", type=int, default=SEED, help="Random seed for deterministic output.")
    parser.add_argument(
        "--postgres",
        action="store_true",
        help="Write to Postgres using DATABASE_URL env var.",
    )
    args = parser.parse_args()

    fake = Faker()
    fake.seed_instance(args.seed)
    rng = random.Random(args.seed)

    # Generate dimension tables
    customers = _build_customer_pool(fake)
    products = _build_products()
    product_prices = _build_product_prices(rng)

    # Generate fact tables
    orders, order_items, payments = generate_orders(days=args.days, seed=args.seed)
    events = generate_events(days=args.days, seed=args.seed)

    if args.postgres:
        import os
        database_url = os.environ.get("DATABASE_URL")
        if not database_url:
            print("ERROR: DATABASE_URL env var is required when using --postgres")
            raise SystemExit(1)
        write_to_postgres(customers, products, product_prices, orders, order_items, payments, events, database_url=database_url)
    else:
        # Write as partitioned JSON landing files
        streams = {
            "customers": customers,
            "products": products,
            "product_prices": product_prices,
            "orders": orders,
            "order_items": order_items,
            "payments": payments,
            "events": events,
        }
        for name, records in streams.items():
            files = write_partitioned_json(records, name)
            print(f"  {name}: {len(files)} file(s), {len(records)} records")

"""Data access layer — all SQL lives here."""

from db import get_conn


# ---------------------------------------------------------------------------
# Customers
# ---------------------------------------------------------------------------

def find_customers(limit: int, offset: int) -> list[dict]:
    con = get_conn()
    cur = con.cursor()
    cur.execute("SELECT * FROM customers ORDER BY customer_id LIMIT %s OFFSET %s", (limit, offset))
    rows = [dict(r) for r in cur.fetchall()]
    cur.close()
    con.close()
    return rows


def find_customer_by_id(customer_id: str) -> dict | None:
    con = get_conn()
    cur = con.cursor()
    cur.execute("SELECT * FROM customers WHERE customer_id = %s", (customer_id,))
    row = cur.fetchone()
    cur.close()
    con.close()
    return dict(row) if row else None


# ---------------------------------------------------------------------------
# Products
# ---------------------------------------------------------------------------

def find_products() -> list[dict]:
    con = get_conn()
    cur = con.cursor()
    cur.execute("SELECT * FROM products ORDER BY product_id")
    rows = [dict(r) for r in cur.fetchall()]
    cur.close()
    con.close()
    return rows


def find_product_by_id(product_id: str) -> dict | None:
    con = get_conn()
    cur = con.cursor()
    cur.execute("SELECT * FROM products WHERE product_id = %s", (product_id,))
    row = cur.fetchone()
    cur.close()
    con.close()
    return dict(row) if row else None


def find_product_prices(product_id: str) -> list[dict]:
    con = get_conn()
    cur = con.cursor()
    cur.execute(
        "SELECT * FROM product_prices WHERE product_id = %s ORDER BY valid_from DESC",
        (product_id,),
    )
    rows = [dict(r) for r in cur.fetchall()]
    cur.close()
    con.close()
    return rows


def get_current_price(product_id: str) -> float | None:
    con = get_conn()
    cur = con.cursor()
    cur.execute(
        "SELECT price FROM product_prices WHERE product_id = %s AND valid_to IS NULL",
        (product_id,),
    )
    row = cur.fetchone()
    cur.close()
    con.close()
    return float(row["price"]) if row else None


# ---------------------------------------------------------------------------
# Orders
# ---------------------------------------------------------------------------

def find_orders(limit: int, offset: int, customer_id: str | None = None, status: str | None = None) -> list[dict]:
    con = get_conn()
    cur = con.cursor()

    query = "SELECT * FROM orders WHERE 1=1"
    params: list = []

    if customer_id:
        query += " AND customer_id = %s"
        params.append(customer_id)
    if status:
        query += " AND status = %s"
        params.append(status)

    query += " ORDER BY placed_at DESC LIMIT %s OFFSET %s"
    params.extend([limit, offset])

    cur.execute(query, params)
    rows = [dict(r) for r in cur.fetchall()]
    cur.close()
    con.close()
    return rows


def find_order_by_id(order_id: str) -> dict | None:
    con = get_conn()
    cur = con.cursor()
    cur.execute("SELECT * FROM orders WHERE order_id = %s", (order_id,))
    row = cur.fetchone()
    cur.close()
    con.close()
    return dict(row) if row else None


def find_order_items(order_id: str) -> list[dict]:
    con = get_conn()
    cur = con.cursor()
    cur.execute("SELECT * FROM order_items WHERE order_id = %s ORDER BY order_item_id", (order_id,))
    rows = [dict(r) for r in cur.fetchall()]
    cur.close()
    con.close()
    return rows


def find_order_payments(order_id: str) -> list[dict]:
    con = get_conn()
    cur = con.cursor()
    cur.execute("SELECT * FROM payments WHERE order_id = %s", (order_id,))
    rows = [dict(r) for r in cur.fetchall()]
    cur.close()
    con.close()
    return rows


def insert_order(order_id: str, customer_id: str, order_total: float, placed_at, updated_at) -> None:
    con = get_conn()
    cur = con.cursor()
    cur.execute(
        "INSERT INTO orders (order_id, customer_id, status, order_total, currency, placed_at, updated_at) VALUES (%s,%s,%s,%s,%s,%s,%s)",
        (order_id, customer_id, "placed", order_total, "USD", placed_at, updated_at),
    )
    con.commit()
    cur.close()
    con.close()


def insert_order_item(order_item_id: str, order_id: str, product_id: str, quantity: int, unit_price: float, line_total: float) -> None:
    con = get_conn()
    cur = con.cursor()
    cur.execute(
        "INSERT INTO order_items (order_item_id, order_id, product_id, quantity, unit_price, line_total) VALUES (%s,%s,%s,%s,%s,%s)",
        (order_item_id, order_id, product_id, quantity, unit_price, line_total),
    )
    con.commit()
    cur.close()
    con.close()


def insert_payment(payment_id: str, order_id: str, amount: float, method: str, paid_at) -> None:
    con = get_conn()
    cur = con.cursor()
    cur.execute(
        "INSERT INTO payments (payment_id, order_id, amount, currency, method, status, paid_at) VALUES (%s,%s,%s,%s,%s,%s,%s)",
        (payment_id, order_id, amount, "USD", method, "completed", paid_at),
    )
    con.commit()
    cur.close()
    con.close()


def decrement_stock(product_id: str, quantity: int) -> None:
    con = get_conn()
    cur = con.cursor()
    cur.execute(
        "UPDATE products SET stock_quantity = stock_quantity - %s WHERE product_id = %s",
        (quantity, product_id),
    )
    con.commit()
    cur.close()
    con.close()


def create_order_transaction(
    order_id: str,
    customer_id: str,
    order_total: float,
    placed_at,
    items: list[dict],
    payment_id: str,
    payment_method: str,
) -> None:
    """Insert order, items, payment, and decrement stock in a single transaction."""
    con = get_conn()
    cur = con.cursor()

    cur.execute(
        "INSERT INTO orders (order_id, customer_id, status, order_total, currency, placed_at, updated_at) VALUES (%s,%s,%s,%s,%s,%s,%s)",
        (order_id, customer_id, "placed", order_total, "USD", placed_at, placed_at),
    )

    for item in items:
        cur.execute(
            "INSERT INTO order_items (order_item_id, order_id, product_id, quantity, unit_price, line_total) VALUES (%s,%s,%s,%s,%s,%s)",
            (item["order_item_id"], order_id, item["product_id"], item["quantity"], item["unit_price"], item["line_total"]),
        )
        cur.execute(
            "UPDATE products SET stock_quantity = stock_quantity - %s WHERE product_id = %s",
            (item["quantity"], item["product_id"]),
        )

    cur.execute(
        "INSERT INTO payments (payment_id, order_id, amount, currency, method, status, paid_at) VALUES (%s,%s,%s,%s,%s,%s,%s)",
        (payment_id, order_id, order_total, "USD", payment_method, "completed", placed_at),
    )

    con.commit()
    cur.close()
    con.close()


# ---------------------------------------------------------------------------
# Events
# ---------------------------------------------------------------------------

def find_events(limit: int, offset: int, event_type: str | None = None, customer_id: str | None = None, session_id: str | None = None) -> list[dict]:
    con = get_conn()
    cur = con.cursor()

    query = "SELECT * FROM events WHERE 1=1"
    params: list = []

    if event_type:
        query += " AND event_type = %s"
        params.append(event_type)
    if customer_id:
        query += " AND customer_id = %s"
        params.append(customer_id)
    if session_id:
        query += " AND session_id = %s"
        params.append(session_id)

    query += " ORDER BY event_time DESC LIMIT %s OFFSET %s"
    params.extend([limit, offset])

    cur.execute(query, params)
    rows = [dict(r) for r in cur.fetchall()]
    cur.close()
    con.close()
    return rows


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------

def get_order_count() -> int:
    con = get_conn()
    cur = con.cursor()
    cur.execute("SELECT count(*) as cnt FROM orders")
    count = cur.fetchone()["cnt"]
    cur.close()
    con.close()
    return count

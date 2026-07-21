"""
API serving generated ecommerce data from Postgres.

Requires DATABASE_URL env var.

Run locally:
    export DATABASE_URL=postgres://dabag:dabag_pw@localhost:5433/dabag
    python gen.py --postgres --days 22
    uvicorn api:app --reload --port 8000

Endpoints:
    GET  /customers
    GET  /customers/{customer_id}
    GET  /products
    GET  /products/{product_id}
    GET  /products/{product_id}/prices
    GET  /orders
    GET  /orders/{order_id}
    GET  /orders/{order_id}/items
    GET  /orders/{order_id}/payments
    POST /orders
    GET  /events
    GET  /health
"""

import os
from datetime import UTC, datetime
from uuid import uuid4

import psycopg2
from psycopg2.extras import RealDictCursor
from fastapi import FastAPI, Query, HTTPException, status
from pydantic import BaseModel

app = FastAPI(
    title="GoodBuy Ecommerce API",
    description="Ecommerce API backed by Postgres.",
)

DATABASE_URL = os.environ.get("DATABASE_URL", "")

PAYMENT_METHODS = ["credit_card", "debit_card", "paypal", "apple_pay", "google_pay"]


def get_conn():
    return psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)


# ---------------------------------------------------------------------------
# Customers
# ---------------------------------------------------------------------------

@app.get("/customers")
def list_customers(
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
):
    con = get_conn()
    cur = con.cursor()
    cur.execute("SELECT * FROM customers ORDER BY customer_id LIMIT %s OFFSET %s", (limit, offset))
    rows = cur.fetchall()
    cur.close()
    con.close()
    return [dict(r) for r in rows]


@app.get("/customers/{customer_id}")
def get_customer(customer_id: str):
    con = get_conn()
    cur = con.cursor()
    cur.execute("SELECT * FROM customers WHERE customer_id = %s", (customer_id,))
    row = cur.fetchone()
    cur.close()
    con.close()
    if not row:
        raise HTTPException(status_code=404, detail="Customer not found")
    return dict(row)


# ---------------------------------------------------------------------------
# Products
# ---------------------------------------------------------------------------

@app.get("/products")
def list_products():
    con = get_conn()
    cur = con.cursor()
    cur.execute("SELECT * FROM products ORDER BY product_id")
    rows = cur.fetchall()
    cur.close()
    con.close()
    return [dict(r) for r in rows]


@app.get("/products/{product_id}")
def get_product(product_id: str):
    con = get_conn()
    cur = con.cursor()
    cur.execute("SELECT * FROM products WHERE product_id = %s", (product_id,))
    row = cur.fetchone()
    cur.close()
    con.close()
    if not row:
        raise HTTPException(status_code=404, detail="Product not found")
    return dict(row)


@app.get("/products/{product_id}/prices")
def get_product_prices(product_id: str):
    con = get_conn()
    cur = con.cursor()
    cur.execute(
        "SELECT * FROM product_prices WHERE product_id = %s ORDER BY valid_from DESC",
        (product_id,),
    )
    rows = cur.fetchall()
    cur.close()
    con.close()
    if not rows:
        raise HTTPException(status_code=404, detail="Product not found")
    return [dict(r) for r in rows]


# ---------------------------------------------------------------------------
# Orders
# ---------------------------------------------------------------------------

@app.get("/orders")
def list_orders(
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    customer_id: str | None = Query(default=None),
    status: str | None = Query(default=None),
):
    con = get_conn()
    cur = con.cursor()

    query = "SELECT * FROM orders WHERE 1=1"
    params = []

    if customer_id:
        query += " AND customer_id = %s"
        params.append(customer_id)
    if status:
        query += " AND status = %s"
        params.append(status)

    query += " ORDER BY placed_at DESC LIMIT %s OFFSET %s"
    params.extend([limit, offset])

    cur.execute(query, params)
    rows = cur.fetchall()
    cur.close()
    con.close()
    return [dict(r) for r in rows]


@app.get("/orders/{order_id}")
def get_order(order_id: str):
    con = get_conn()
    cur = con.cursor()
    cur.execute("SELECT * FROM orders WHERE order_id = %s", (order_id,))
    row = cur.fetchone()
    cur.close()
    con.close()
    if not row:
        raise HTTPException(status_code=404, detail="Order not found")
    return dict(row)


@app.get("/orders/{order_id}/items")
def get_order_items(order_id: str):
    con = get_conn()
    cur = con.cursor()
    cur.execute("SELECT * FROM order_items WHERE order_id = %s ORDER BY order_item_id", (order_id,))
    rows = cur.fetchall()
    cur.close()
    con.close()
    if not rows:
        raise HTTPException(status_code=404, detail="Order not found or has no items")
    return [dict(r) for r in rows]


@app.get("/orders/{order_id}/payments")
def get_order_payments(order_id: str):
    con = get_conn()
    cur = con.cursor()
    cur.execute("SELECT * FROM payments WHERE order_id = %s", (order_id,))
    rows = cur.fetchall()
    cur.close()
    con.close()
    if not rows:
        raise HTTPException(status_code=404, detail="Order not found or has no payments")
    return [dict(r) for r in rows]


# --- POST /orders ---

class OrderItemCreate(BaseModel):
    product_id: str
    quantity: int


class PaymentCreate(BaseModel):
    method: str  # credit_card, debit_card, paypal, apple_pay, google_pay


class OrderCreate(BaseModel):
    customer_id: str
    items: list[OrderItemCreate]
    payment: PaymentCreate


@app.post("/orders", status_code=status.HTTP_201_CREATED)
def create_order(order: OrderCreate):
    con = get_conn()
    cur = con.cursor()

    # Validate customer exists
    cur.execute("SELECT customer_id FROM customers WHERE customer_id = %s", (order.customer_id,))
    if not cur.fetchone():
        cur.close()
        con.close()
        raise HTTPException(status_code=400, detail=f"Customer {order.customer_id} not found")

    # Validate payment method
    if order.payment.method not in PAYMENT_METHODS:
        cur.close()
        con.close()
        raise HTTPException(
            status_code=400,
            detail=f"Invalid payment method '{order.payment.method}'. Must be one of: {PAYMENT_METHODS}",
        )

    # Validate each product exists and has enough stock
    order_total = 0.0
    validated_items = []

    for item in order.items:
        if item.quantity < 1:
            cur.close()
            con.close()
            raise HTTPException(status_code=400, detail=f"Quantity must be at least 1 for {item.product_id}")

        cur.execute("SELECT product_id, name, stock_quantity FROM products WHERE product_id = %s", (item.product_id,))
        product = cur.fetchone()

        if not product:
            cur.close()
            con.close()
            raise HTTPException(status_code=400, detail=f"Product {item.product_id} not found")

        if product["stock_quantity"] < item.quantity:
            cur.close()
            con.close()
            raise HTTPException(
                status_code=400,
                detail=f"Insufficient stock for {product['name']}. Available: {product['stock_quantity']}, requested: {item.quantity}",
            )

        # Get current price
        cur.execute(
            "SELECT price FROM product_prices WHERE product_id = %s AND valid_to IS NULL",
            (item.product_id,),
        )
        price_row = cur.fetchone()
        unit_price = float(price_row["price"]) if price_row else 0.0
        line_total = round(unit_price * item.quantity, 2)
        order_total += line_total

        validated_items.append({
            "product_id": item.product_id,
            "quantity": item.quantity,
            "unit_price": unit_price,
            "line_total": line_total,
        })

    order_total = round(order_total, 2)
    now = datetime.now(UTC)

    # Generate IDs
    order_id = f"O-{uuid4().hex[:8].upper()}"
    payment_id = f"PAY-{uuid4().hex[:8].upper()}"

    # Insert order
    cur.execute(
        "INSERT INTO orders (order_id, customer_id, status, order_total, currency, placed_at, updated_at) VALUES (%s,%s,%s,%s,%s,%s,%s)",
        (order_id, order.customer_id, "placed", order_total, "USD", now, now),
    )

    # Insert order items and decrement stock
    for idx, item in enumerate(validated_items):
        order_item_id = f"OI-{uuid4().hex[:8].upper()}"
        cur.execute(
            "INSERT INTO order_items (order_item_id, order_id, product_id, quantity, unit_price, line_total) VALUES (%s,%s,%s,%s,%s,%s)",
            (order_item_id, order_id, item["product_id"], item["quantity"], item["unit_price"], item["line_total"]),
        )
        # Decrement stock
        cur.execute(
            "UPDATE products SET stock_quantity = stock_quantity - %s WHERE product_id = %s",
            (item["quantity"], item["product_id"]),
        )

    # Insert payment
    cur.execute(
        "INSERT INTO payments (payment_id, order_id, amount, currency, method, status, paid_at) VALUES (%s,%s,%s,%s,%s,%s,%s)",
        (payment_id, order_id, order_total, "USD", order.payment.method, "completed", now),
    )

    con.commit()
    cur.close()
    con.close()

    return {
        "order_id": order_id,
        "customer_id": order.customer_id,
        "status": "placed",
        "order_total": order_total,
        "currency": "USD",
        "items": validated_items,
        "payment": {
            "payment_id": payment_id,
            "method": order.payment.method,
            "status": "completed",
            "amount": order_total,
        },
        "placed_at": now.isoformat(),
    }

# ---------------------------------------------------------------------------
# Events
# ---------------------------------------------------------------------------

@app.get("/events")
def list_events(
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    event_type: str | None = Query(default=None),
    customer_id: str | None = Query(default=None),
    session_id: str | None = Query(default=None),
):
    con = get_conn()
    cur = con.cursor()

    query = "SELECT * FROM events WHERE 1=1"
    params = []

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
    rows = cur.fetchall()
    cur.close()
    con.close()
    return [dict(r) for r in rows]


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------

@app.get("/health")
def health():
    try:
        con = get_conn()
        cur = con.cursor()
        cur.execute("SELECT count(*) as cnt FROM orders")
        count = cur.fetchone()["cnt"]
        cur.close()
        con.close()
        return {"status": "ok", "orders_count": count}
    except Exception as e:
        return {"status": "error", "detail": str(e)}

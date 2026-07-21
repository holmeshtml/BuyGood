"""
Read-only API serving generated ecommerce data from Postgres.

Requires DATABASE_URL env var.

Run locally:
    export DATABASE_URL=postgres://dabag:dabag_pw@localhost:5433/dabag
    python gen.py --postgres --days 22
    uvicorn api:app --reload --port 8000

Endpoints:
    GET /customers
    GET /customers/{customer_id}
    GET /products
    GET /products/{product_id}
    GET /products/{product_id}/prices
    GET /orders
    GET /orders/{order_id}
    GET /orders/{order_id}/items
    GET /orders/{order_id}/payments
    GET /events
    GET /health
"""

import os

import psycopg2
from psycopg2.extras import RealDictCursor
from fastapi import FastAPI, Query, HTTPException

app = FastAPI(
    title="GoodBuy Ecommerce API",
    description="Read-only API for generated ecommerce data backed by Postgres.",
)

DATABASE_URL = os.environ.get("DATABASE_URL", "")


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

"""
Read-only API serving generated ecommerce data from a baked-in DuckDB file.

Run locally:
    python gen.py --duckdb
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

import duckdb
from fastapi import FastAPI, Query, HTTPException

app = FastAPI(
    title="GoodBuy Ecommerce API",
    description="Read-only API for generated ecommerce data backed by DuckDB.",
)

DB_PATH = "goodbuy.duckdb"


def get_conn():
    return duckdb.connect(DB_PATH, read_only=True)


# ---------------------------------------------------------------------------
# Customers
# ---------------------------------------------------------------------------

@app.get("/customers")
def list_customers(
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
):
    con = get_conn()
    rows = con.execute(
        "SELECT * FROM customers ORDER BY customer_id LIMIT ? OFFSET ?",
        [limit, offset],
    ).fetchall()
    columns = [desc[0] for desc in con.description]
    con.close()
    return [dict(zip(columns, row)) for row in rows]


@app.get("/customers/{customer_id}")
def get_customer(customer_id: str):
    con = get_conn()
    rows = con.execute("SELECT * FROM customers WHERE customer_id = ?", [customer_id]).fetchall()
    columns = [desc[0] for desc in con.description]
    con.close()
    if not rows:
        raise HTTPException(status_code=404, detail="Customer not found")
    return dict(zip(columns, rows[0]))


# ---------------------------------------------------------------------------
# Products
# ---------------------------------------------------------------------------

@app.get("/products")
def list_products():
    con = get_conn()
    rows = con.execute("SELECT * FROM products ORDER BY product_id").fetchall()
    columns = [desc[0] for desc in con.description]
    con.close()
    return [dict(zip(columns, row)) for row in rows]


@app.get("/products/{product_id}")
def get_product(product_id: str):
    con = get_conn()
    rows = con.execute("SELECT * FROM products WHERE product_id = ?", [product_id]).fetchall()
    columns = [desc[0] for desc in con.description]
    con.close()
    if not rows:
        raise HTTPException(status_code=404, detail="Product not found")
    return dict(zip(columns, rows[0]))


@app.get("/products/{product_id}/prices")
def get_product_prices(product_id: str):
    con = get_conn()
    rows = con.execute(
        "SELECT * FROM product_prices WHERE product_id = ? ORDER BY valid_from DESC",
        [product_id],
    ).fetchall()
    columns = [desc[0] for desc in con.description]
    con.close()
    if not rows:
        raise HTTPException(status_code=404, detail="Product not found")
    return [dict(zip(columns, row)) for row in rows]


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
    query = "SELECT * FROM orders WHERE 1=1"
    params = []

    if customer_id:
        query += " AND customer_id = ?"
        params.append(customer_id)
    if status:
        query += " AND status = ?"
        params.append(status)

    query += " ORDER BY placed_at DESC LIMIT ? OFFSET ?"
    params.extend([limit, offset])

    rows = con.execute(query, params).fetchall()
    columns = [desc[0] for desc in con.description]
    con.close()
    return [dict(zip(columns, row)) for row in rows]


@app.get("/orders/{order_id}")
def get_order(order_id: str):
    con = get_conn()
    rows = con.execute("SELECT * FROM orders WHERE order_id = ?", [order_id]).fetchall()
    columns = [desc[0] for desc in con.description]
    con.close()
    if not rows:
        raise HTTPException(status_code=404, detail="Order not found")
    return dict(zip(columns, rows[0]))


@app.get("/orders/{order_id}/items")
def get_order_items(order_id: str):
    con = get_conn()
    rows = con.execute(
        "SELECT * FROM order_items WHERE order_id = ? ORDER BY order_item_id",
        [order_id],
    ).fetchall()
    columns = [desc[0] for desc in con.description]
    con.close()
    if not rows:
        raise HTTPException(status_code=404, detail="Order not found or has no items")
    return [dict(zip(columns, row)) for row in rows]


@app.get("/orders/{order_id}/payments")
def get_order_payments(order_id: str):
    con = get_conn()
    rows = con.execute(
        "SELECT * FROM payments WHERE order_id = ?",
        [order_id],
    ).fetchall()
    columns = [desc[0] for desc in con.description]
    con.close()
    if not rows:
        raise HTTPException(status_code=404, detail="Order not found or has no payments")
    return [dict(zip(columns, row)) for row in rows]


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
    query = "SELECT * FROM events WHERE 1=1"
    params = []

    if event_type:
        query += " AND event_type = ?"
        params.append(event_type)
    if customer_id:
        query += " AND customer_id = ?"
        params.append(customer_id)
    if session_id:
        query += " AND session_id = ?"
        params.append(session_id)

    query += " ORDER BY event_time DESC LIMIT ? OFFSET ?"
    params.extend([limit, offset])

    rows = con.execute(query, params).fetchall()
    columns = [desc[0] for desc in con.description]
    con.close()
    return [dict(zip(columns, row)) for row in rows]


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------

@app.get("/health")
def health():
    con = get_conn()
    count = con.execute("SELECT count(*) FROM orders").fetchone()[0]
    con.close()
    return {"status": "ok", "orders_count": count}

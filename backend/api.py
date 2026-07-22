"""
Thin route layer — no SQL, no business logic.

Run locally:
    export DATABASE_URL=postgres://dabag:dabag_pw@localhost:5433/dabag
    python gen.py --postgres --days 22
    uvicorn api:app --reload --port 8000
"""

from fastapi import FastAPI, Query, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

import repository
import services
from services import ServiceError

app = FastAPI(
    title="GoodBuy Ecommerce API",
    description="Ecommerce API backed by Postgres.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Request schemas
# ---------------------------------------------------------------------------

class OrderItemCreate(BaseModel):
    product_id: str
    quantity: int


class PaymentCreate(BaseModel):
    method: str


class OrderCreate(BaseModel):
    customer_id: str
    items: list[OrderItemCreate]
    payment: PaymentCreate


# ---------------------------------------------------------------------------
# Customers
# ---------------------------------------------------------------------------

@app.get("/customers")
def list_customers(
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
):
    return repository.find_customers(limit, offset)


@app.get("/customers/{customer_id}")
def get_customer(customer_id: str):
    customer = repository.find_customer_by_id(customer_id)
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    return customer


# ---------------------------------------------------------------------------
# Products
# ---------------------------------------------------------------------------

@app.get("/products")
def list_products():
    return repository.find_products()


@app.get("/products/{product_id}")
def get_product(product_id: str):
    product = repository.find_product_by_id(product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product


@app.get("/products/{product_id}/prices")
def get_product_prices(product_id: str):
    prices = repository.find_product_prices(product_id)
    if not prices:
        raise HTTPException(status_code=404, detail="Product not found")
    return prices


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
    return repository.find_orders(limit, offset, customer_id=customer_id, status=status)


@app.get("/orders/{order_id}")
def get_order(order_id: str):
    order = repository.find_order_by_id(order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return order


@app.get("/orders/{order_id}/items")
def get_order_items(order_id: str):
    items = repository.find_order_items(order_id)
    if not items:
        raise HTTPException(status_code=404, detail="Order not found or has no items")
    return items


@app.get("/orders/{order_id}/payments")
def get_order_payments(order_id: str):
    payments = repository.find_order_payments(order_id)
    if not payments:
        raise HTTPException(status_code=404, detail="Order not found or has no payments")
    return payments


@app.post("/orders", status_code=status.HTTP_201_CREATED)
def create_order(order: OrderCreate):
    try:
        result = services.create_order(
            customer_id=order.customer_id,
            items=[{"product_id": i.product_id, "quantity": i.quantity} for i in order.items],
            payment_method=order.payment.method,
        )
        return result
    except ServiceError as e:
        raise HTTPException(status_code=400, detail=e.detail)


# ---------------------------------------------------------------------------
# Search (Natural Language)
# ---------------------------------------------------------------------------

class SearchQuery(BaseModel):
    query: str


@app.post("/orders/search")
def search_orders(body: SearchQuery):
    try:
        result = services.search_orders(query=body.query)
        return result
    except ServiceError as e:
        raise HTTPException(status_code=400, detail=e.detail)


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
    return repository.find_events(limit, offset, event_type=event_type, customer_id=customer_id, session_id=session_id)


# ---------------------------------------------------------------------------
# Seed Data
# ---------------------------------------------------------------------------

@app.post("/seed", status_code=status.HTTP_201_CREATED)
def seed_data(days: int = Query(default=7, ge=1, le=365)):
    """Drop and re-seed the database with fake data for the given number of days."""
    import os
    from faker import Faker
    import random as _random

    from gen import (
        _build_customer_pool,
        _build_products,
        _build_product_prices,
        generate_orders,
        generate_events,
        write_to_postgres,
        SEED,
    )

    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        raise HTTPException(status_code=500, detail="DATABASE_URL not configured")

    fake = Faker()
    fake.seed_instance(SEED)
    rng = _random.Random(SEED)

    customers = _build_customer_pool(fake)
    products = _build_products()
    product_prices = _build_product_prices(rng)
    orders, order_items, payments = generate_orders(days=days, seed=SEED)
    events = generate_events(days=days, seed=SEED)

    write_to_postgres(
        customers, products, product_prices,
        orders, order_items, payments, events,
        database_url=database_url,
    )

    return {
        "status": "seeded",
        "days": days,
        "counts": {
            "customers": len(customers),
            "products": len(products),
            "orders": len(orders),
            "order_items": len(order_items),
            "payments": len(payments),
            "events": len(events),
        },
    }


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------

@app.get("/health")
def health():
    return {"status": "ok"}

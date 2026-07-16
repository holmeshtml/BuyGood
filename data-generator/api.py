"""
Local API that generates ecommerce event data on each request.

Run with:
    uvicorn api:app --reload --port 8000

Endpoints:
    POST /generate/orders
    POST /generate/page_views
    POST /generate/cart_adds
    POST /generate/all

Query params (all optional):
    days            - number of historical days (default 1)
    seed            - random seed; omit for random each call
    backfill_spike  - true/false to amplify late arrivals
    limit           - max events to return (default 500)
"""

import random
import time

from fastapi import FastAPI, Query
from fastapi.responses import JSONResponse

from gen import (
    generate_cart_adds,
    generate_orders,
    generate_page_views,
)

app = FastAPI(
    title="GoodBuy Data Generator API",
    description="Generates fake ecommerce event streams on demand.",
)


def _resolve_seed(seed: int | None) -> int:
    if seed is not None:
        return seed
    return random.randint(0, 2**31)


@app.post("/generate/orders")
def api_generate_orders(
    days: int = Query(default=1, ge=1, le=30),
    seed: int | None = Query(default=None),
    backfill_spike: bool = Query(default=False),
    limit: int = Query(default=500, ge=1, le=5000),
):
    resolved_seed = _resolve_seed(seed)
    start = time.time()

    orders = generate_orders(days=days, seed=resolved_seed, backfill_spike=backfill_spike)
    orders = orders[:limit]

    return JSONResponse(content={
        "event_type": "orders",
        "count": len(orders),
        "seed": resolved_seed,
        "days": days,
        "backfill_spike": backfill_spike,
        "generation_time_ms": round((time.time() - start) * 1000, 1),
        "events": orders,
    })


@app.post("/generate/page_views")
def api_generate_page_views(
    days: int = Query(default=1, ge=1, le=30),
    seed: int | None = Query(default=None),
    backfill_spike: bool = Query(default=False),
    limit: int = Query(default=500, ge=1, le=5000),
):
    resolved_seed = _resolve_seed(seed)
    start = time.time()

    page_views = generate_page_views(days=days, seed=resolved_seed, backfill_spike=backfill_spike)
    page_views = page_views[:limit]

    return JSONResponse(content={
        "event_type": "page_views",
        "count": len(page_views),
        "seed": resolved_seed,
        "days": days,
        "backfill_spike": backfill_spike,
        "generation_time_ms": round((time.time() - start) * 1000, 1),
        "events": page_views,
    })


@app.post("/generate/cart_adds")
def api_generate_cart_adds(
    days: int = Query(default=1, ge=1, le=30),
    seed: int | None = Query(default=None),
    backfill_spike: bool = Query(default=False),
    limit: int = Query(default=500, ge=1, le=5000),
):
    resolved_seed = _resolve_seed(seed)
    start = time.time()

    cart_adds = generate_cart_adds(days=days, seed=resolved_seed, backfill_spike=backfill_spike)
    cart_adds = cart_adds[:limit]

    return JSONResponse(content={
        "event_type": "cart_adds",
        "count": len(cart_adds),
        "seed": resolved_seed,
        "days": days,
        "backfill_spike": backfill_spike,
        "generation_time_ms": round((time.time() - start) * 1000, 1),
        "events": cart_adds,
    })


@app.post("/generate/all")
def api_generate_all(
    days: int = Query(default=1, ge=1, le=30),
    seed: int | None = Query(default=None),
    backfill_spike: bool = Query(default=False),
    limit: int = Query(default=500, ge=1, le=5000),
):
    resolved_seed = _resolve_seed(seed)
    start = time.time()

    orders = generate_orders(days=days, seed=resolved_seed, backfill_spike=backfill_spike)[:limit]
    page_views = generate_page_views(days=days, seed=resolved_seed, backfill_spike=backfill_spike)[:limit]
    cart_adds = generate_cart_adds(days=days, seed=resolved_seed, backfill_spike=backfill_spike)[:limit]

    return JSONResponse(content={
        "seed": resolved_seed,
        "days": days,
        "backfill_spike": backfill_spike,
        "generation_time_ms": round((time.time() - start) * 1000, 1),
        "orders": {"count": len(orders), "events": orders},
        "page_views": {"count": len(page_views), "events": page_views},
        "cart_adds": {"count": len(cart_adds), "events": cart_adds},
    })


@app.get("/health")
def health():
    return {"status": "ok"}

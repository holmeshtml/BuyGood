"""Business logic layer — validation and orchestration live here."""

import os
from datetime import UTC, datetime
from uuid import uuid4

import anthropic

import repository

PAYMENT_METHODS = ["credit_card", "debit_card", "paypal", "apple_pay", "google_pay"]

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")


class ServiceError(Exception):
    """Raised when a business rule is violated."""

    def __init__(self, detail: str):
        self.detail = detail


def create_order(customer_id: str, items: list[dict], payment_method: str) -> dict:
    """Validate inputs and create an order with items and payment.

    Args:
        customer_id: Must be an existing customer.
        items: List of {"product_id": str, "quantity": int}.
        payment_method: Must be one of PAYMENT_METHODS.

    Returns:
        Dict with full order details.

    Raises:
        ServiceError: On any validation failure.
    """
    # Validate customer
    customer = repository.find_customer_by_id(customer_id)
    if not customer:
        raise ServiceError(f"Customer {customer_id} not found")

    # Validate payment method
    if payment_method not in PAYMENT_METHODS:
        raise ServiceError(f"Invalid payment method '{payment_method}'. Must be one of: {PAYMENT_METHODS}")

    # Validate products and stock
    order_total = 0.0
    validated_items = []

    for item in items:
        if item["quantity"] < 1:
            raise ServiceError(f"Quantity must be at least 1 for {item['product_id']}")

        product = repository.find_product_by_id(item["product_id"])
        if not product:
            raise ServiceError(f"Product {item['product_id']} not found")

        if product["stock_quantity"] < item["quantity"]:
            raise ServiceError(
                f"Insufficient stock for {product['name']}. "
                f"Available: {product['stock_quantity']}, requested: {item['quantity']}"
            )

        unit_price = repository.get_current_price(item["product_id"])
        if unit_price is None:
            raise ServiceError(f"No current price found for {item['product_id']}")

        line_total = round(unit_price * item["quantity"], 2)
        order_total += line_total

        validated_items.append({
            "order_item_id": f"OI-{uuid4().hex[:8].upper()}",
            "product_id": item["product_id"],
            "quantity": item["quantity"],
            "unit_price": unit_price,
            "line_total": line_total,
        })

    order_total = round(order_total, 2)
    now = datetime.now(UTC)
    order_id = f"O-{uuid4().hex[:8].upper()}"
    payment_id = f"PAY-{uuid4().hex[:8].upper()}"

    # Persist everything in one transaction
    repository.create_order_transaction(
        order_id=order_id,
        customer_id=customer_id,
        order_total=order_total,
        placed_at=now,
        items=validated_items,
        payment_id=payment_id,
        payment_method=payment_method,
    )

    return {
        "order_id": order_id,
        "customer_id": customer_id,
        "status": "placed",
        "order_total": order_total,
        "currency": "USD",
        "items": [
            {
                "product_id": i["product_id"],
                "quantity": i["quantity"],
                "unit_price": i["unit_price"],
                "line_total": i["line_total"],
            }
            for i in validated_items
        ],
        "payment": {
            "payment_id": payment_id,
            "method": payment_method,
            "status": "completed",
            "amount": order_total,
        },
        "placed_at": now.isoformat(),
    }


def search_orders(query: str) -> dict:
    """Use Claude to translate a natural language query into SQL, run it, and return results.

    Three layers of defense:
    1. Only SELECT statements are allowed (hard reject on anything else).
    2. Query runs inside a read-only transaction (SET TRANSACTION READ ONLY).
    3. The generated SQL is always shown back to the caller for transparency.

    Falls back to recent orders if the AI-generated query fails execution.
    """
    if not ANTHROPIC_API_KEY:
        raise ServiceError("ANTHROPIC_API_KEY env var is not set")

    schema_description = """
    You have access to these Postgres tables:

    orders (order_id VARCHAR PK, customer_id VARCHAR, status VARCHAR, order_total NUMERIC(10,2), currency VARCHAR, placed_at TIMESTAMPTZ, updated_at TIMESTAMPTZ)
    order_items (order_item_id VARCHAR PK, order_id VARCHAR FK, product_id VARCHAR FK, quantity INTEGER, unit_price NUMERIC(10,2), line_total NUMERIC(10,2))
    payments (payment_id VARCHAR PK, order_id VARCHAR FK, amount NUMERIC(10,2), currency VARCHAR, method VARCHAR, status VARCHAR, paid_at TIMESTAMPTZ)
    customers (customer_id VARCHAR PK, full_name VARCHAR, email VARCHAR, phone VARCHAR, address VARCHAR, created_at TIMESTAMPTZ)
    products (product_id VARCHAR PK, name VARCHAR, category VARCHAR, stock_quantity INTEGER, created_at TIMESTAMPTZ)
    product_prices (product_id VARCHAR FK, price NUMERIC(10,2), currency VARCHAR, valid_from TIMESTAMPTZ, valid_to TIMESTAMPTZ)
    events (event_id VARCHAR PK, event_type VARCHAR, session_id VARCHAR, customer_id VARCHAR, event_time TIMESTAMPTZ, device VARCHAR, referrer VARCHAR, page_path VARCHAR, product_id VARCHAR, quantity INTEGER)

    Status values for orders: 'placed', 'shipped', 'refunded'
    Status values for payments: 'completed', 'refunded'
    Payment methods: 'credit_card', 'debit_card', 'paypal', 'apple_pay', 'google_pay'
    """

    prompt = f"""Given this database schema:
{schema_description}

Convert this natural language query into a single SELECT SQL statement:
"{query}"

Rules:
- Return ONLY the SQL query, no explanation, no markdown, no code fences.
- Always LIMIT results to 50 rows max.
- Only generate SELECT statements, never INSERT/UPDATE/DELETE/DROP.
- If the query is ambiguous, make reasonable assumptions.
"""

    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    message = client.messages.create(
        model="claude-3-5-sonnet-20241022",
        max_tokens=500,
        messages=[{"role": "user", "content": prompt}],
    )

    generated_sql = message.content[0].text.strip()

    # --- GUARDRAIL 1: Only allow SELECT, block dangerous keywords ---
    sql_upper = generated_sql.upper().lstrip()
    if not sql_upper.startswith("SELECT"):
        raise ServiceError("Generated query is not a SELECT statement. Refusing to execute.")

    dangerous_keywords = ["INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "TRUNCATE", "CREATE", "GRANT", "REVOKE"]
    sql_tokens = generated_sql.upper().split()
    for keyword in dangerous_keywords:
        if keyword in sql_tokens:
            raise ServiceError(f"Generated query contains forbidden keyword '{keyword}'. Refusing to execute.")

    # --- GUARDRAIL 2: Execute in a read-only transaction ---
    from db import get_conn

    con = get_conn()
    cur = con.cursor()

    try:
        cur.execute("SET TRANSACTION READ ONLY")
        cur.execute(generated_sql)
        rows = [dict(r) for r in cur.fetchall()]
        con.rollback()  # Read-only — always rollback, nothing to persist
    except Exception as e:
        con.rollback()
        cur.close()
        con.close()

        # --- GUARDRAIL 3: Fallback to recent orders instead of hard error ---
        fallback_con = get_conn()
        fallback_cur = fallback_con.cursor()
        fallback_cur.execute("SELECT * FROM orders ORDER BY placed_at DESC LIMIT 20")
        fallback_rows = [dict(r) for r in fallback_cur.fetchall()]
        fallback_cur.close()
        fallback_con.close()

        return {
            "query": query,
            "generated_sql": generated_sql,
            "error": f"Query failed: {str(e)}. Showing recent orders as fallback.",
            "results": fallback_rows,
            "count": len(fallback_rows),
            "is_fallback": True,
        }

    cur.close()
    con.close()

    # --- Always return the generated SQL for transparency ---
    return {
        "query": query,
        "generated_sql": generated_sql,
        "results": rows,
        "count": len(rows),
        "is_fallback": False,
    }

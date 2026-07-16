with orders as (
    select * from {{ ref('stg_orders') }}
),

daily as (
    select
        cast(placed_at as date) as order_date,
        count(*) as total_orders,
        sum(order_total) as total_revenue,
        avg(order_total) as avg_order_value,
        sum(case when current_status = 'refunded' then 1 else 0 end) as refunded_orders,
        sum(case when current_status = 'refunded' then order_total else 0 end) as refunded_revenue
    from orders
    group by cast(placed_at as date)
)

select
    order_date,
    total_orders,
    total_revenue,
    avg_order_value,
    refunded_orders,
    refunded_revenue,
    total_revenue - refunded_revenue as net_revenue
from daily

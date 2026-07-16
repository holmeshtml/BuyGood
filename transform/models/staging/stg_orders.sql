with source as (
    select * from {{ source('buygood_raw', 'raw_orders') }}
),

staged as (
    select
        order_id,
        customer_id,
        cast(event_time as datetime2) as event_time,
        cast(placed_at as datetime2) as placed_at,
        cast(ingested_time as datetime2) as ingested_time,
        late_bucket,
        ingestion_delay_seconds,
        current_status,
        order_total,
        currency
    from source
)

select * from staged

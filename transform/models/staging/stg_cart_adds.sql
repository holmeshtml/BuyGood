with source as (
    select * from {{ source('buygood_raw', 'raw_cart_adds') }}
),

staged as (
    select
        cart_add_id,
        session_id,
        customer_id,
        cast(event_time as datetime2) as event_time,
        cast(ingested_time as datetime2) as ingested_time,
        late_bucket,
        ingestion_delay_seconds,
        product_id,
        product_name,
        unit_price,
        quantity,
        cart_add_value
    from source
)

select * from staged

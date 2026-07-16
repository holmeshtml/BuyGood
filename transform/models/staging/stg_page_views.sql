with source as (
    select * from {{ source('buygood_raw', 'raw_page_views') }}
),

staged as (
    select
        page_view_id,
        session_id,
        customer_id,
        cast(event_time as datetime2) as event_time,
        cast(ingested_time as datetime2) as ingested_time,
        late_bucket,
        ingestion_delay_seconds,
        page_path,
        referrer,
        device,
        is_logged_in
    from source
)

select * from staged

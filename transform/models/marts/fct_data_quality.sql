-- Tracks ingestion latency and late-arriving data across all streams.
-- Useful for monitoring pipeline health.

with all_events as (
    select
        'orders' as event_type,
        event_time,
        ingested_time,
        late_bucket,
        ingestion_delay_seconds
    from {{ ref('stg_orders') }}

    union all

    select
        'page_views' as event_type,
        event_time,
        ingested_time,
        late_bucket,
        ingestion_delay_seconds
    from {{ ref('stg_page_views') }}

    union all

    select
        'cart_adds' as event_type,
        event_time,
        ingested_time,
        late_bucket,
        ingestion_delay_seconds
    from {{ ref('stg_cart_adds') }}
),

daily_quality as (
    select
        event_type,
        cast(event_time as date) as event_date,
        count(*) as total_events,
        avg(ingestion_delay_seconds) as avg_delay_seconds,
        max(ingestion_delay_seconds) as max_delay_seconds,
        sum(case when late_bucket = 'on_time' then 1 else 0 end) as on_time_count,
        sum(case when late_bucket = 'late_minutes' then 1 else 0 end) as late_minutes_count,
        sum(case when late_bucket = 'late_hours' then 1 else 0 end) as late_hours_count,
        sum(case when late_bucket = 'late_day' then 1 else 0 end) as late_day_count
    from all_events
    group by event_type, cast(event_time as date)
)

select
    event_type,
    event_date,
    total_events,
    avg_delay_seconds,
    max_delay_seconds,
    on_time_count,
    late_minutes_count,
    late_hours_count,
    late_day_count,
    cast(on_time_count as float) / total_events as on_time_rate
from daily_quality

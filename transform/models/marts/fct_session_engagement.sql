with page_views as (
    select * from {{ ref('stg_page_views') }}
),

cart_adds as (
    select * from {{ ref('stg_cart_adds') }}
),

session_views as (
    select
        session_id,
        customer_id,
        device,
        referrer,
        min(event_time) as session_start,
        max(event_time) as session_end,
        count(*) as page_view_count,
        count(distinct page_path) as unique_pages_viewed
    from page_views
    group by session_id, customer_id, device, referrer
),

session_carts as (
    select
        session_id,
        count(*) as cart_add_count,
        sum(cart_add_value) as total_cart_value
    from cart_adds
    group by session_id
)

select
    sv.session_id,
    sv.customer_id,
    sv.device,
    sv.referrer,
    sv.session_start,
    sv.session_end,
    sv.page_view_count,
    sv.unique_pages_viewed,
    coalesce(sc.cart_add_count, 0) as cart_add_count,
    coalesce(sc.total_cart_value, 0) as total_cart_value,
    case when sc.cart_add_count > 0 then 1 else 0 end as has_cart_activity
from session_views sv
left join session_carts sc on sv.session_id = sc.session_id

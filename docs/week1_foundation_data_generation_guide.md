# Week 1: Foundation & Data Generation — In-Depth Guide

Goal for the week: a reproducible fake data source you fully control, landing in a "landing zone" that mimics how raw data arrives in a real system. Everything downstream (Kafka, dbt, Airflow, dashboards) depends on this being solid, so it's worth over-engineering slightly now.

---

## 1. Repo Setup

**Structure the repo around pipeline stages, not tech.** A common mistake is organizing folders by tool (`/kafka`, `/dbt`, `/airflow`) before you know how they'll interact. Instead, organize by what the code *does*:

- A folder for the data generator (the simulator).
- A folder for infrastructure-as-config (Docker Compose files, and later Airflow/dbt configs).
- A folder for the landing zone itself if you're using local flat files (this can also just be a gitignored data directory, since generated data shouldn't be committed).
- A top-level README that will grow week over week — start it now, don't wait until Week 5.

**Decisions to make explicitly, and write down in the README as you go:**

- Python version and dependency manager (plain `venv` + `pip`, or `poetry`/`uv`). For a project like this, a lockfile matters less than reproducibility of the Docker services, but pin it anyway so you don't hit "works on my machine" issues in week 4 when Airflow runs the same code in a container.
- Whether this is a monorepo for the whole project (recommended) or separate repos per stage. Monorepo is easier to demo and easier to reason about for an interview walkthrough.
- Git hygiene: `.gitignore` for generated data, `.env` files, and any local Postgres volumes.

**Why this matters for the interview narrative:** when you describe this project later, "I organized by pipeline stage so the repo mirrors the data flow" is a much stronger answer than "I just put things in folders."

---

## 2. Docker Compose: Postgres (and thinking ahead to Kafka)

Week 1 only needs Postgres, but design the Compose file as if Kafka is coming next week — it'll save you a rewrite.

**Core decisions:**

- **Named volumes, not bind mounts, for Postgres data.** You want the database to persist across `docker compose down` but you also want an easy "nuke and restart" path (`docker compose down -v`) for when you're iterating on schema design. This distinction — ephemeral compute, persistent state — is itself a talking point later ("how do you handle backfill/replay" ties directly into this).
- **Expose Postgres on a non-default host port** if you already run Postgres locally for other projects, to avoid port collisions.
- **Health checks.** Even in Week 1, add a `healthcheck` to the Postgres service. This becomes essential in Week 4 when Airflow needs to know the DB is actually ready before running a DAG, not just that the container started.
- **Environment variables via `.env`, not hardcoded in the Compose file.** This is the pattern you'll extend to Kafka broker configs, MinIO credentials, and eventually Snowflake/BigQuery secrets. Get the habit right now.
- **Network naming.** Give the Compose network an explicit name so that when you add Kafka, MinIO, Airflow, and dbt containers in later weeks, they can all resolve each other by service name without you having to re-architect networking.

**A note on scope:** you don't need to load anything into Postgres yet this week — that's Week 3. Postgres in Week 1 exists so you have a place to eventually query your landed data locally without needing a warehouse account yet, and so you can validate your generator's output makes relational sense (e.g., foreign keys between orders and customers actually resolve) before you formalize it in dbt.

---

## 3. Designing the Data Generator

This is the intellectual core of Week 1. The goal isn't just "produce rows" — it's to produce data with the *shape of real problems*, because the rest of the project (dbt tests, Airflow quality gates, backfill handling) only demonstrates value if there's something realistic to catch.

### 3.1 Entity model

Think in terms of three related streams, because they force you to handle relationships and funnel logic later:

- **Page views** — high volume, low structure. Each view ties to a session and, if the user is logged in, a customer.
- **Cart adds** — medium volume, ties a session/customer to a product and quantity.
- **Orders** — low volume relative to the above, but highest business value. Ties to a customer, contains line items, has a status that changes over time (placed → paid → shipped → possibly refunded).

Designing it as three streams that funnel into each other (view → cart add → order) is what lets your eventual mart models compute **funnel conversion**, which is one of the more interesting deliverables in Week 3. If you only generate orders, you lose that.

### 3.2 Realistic timing

"Realistic timing" means avoiding uniform-random timestamps, which is what naive generators produce and what makes downstream partitioning trivial and boring. Instead:

- **Diurnal and weekly patterns.** Traffic should peak at certain hours and dip overnight; weekends might behave differently from weekdays. This gives your later dashboards something real to show ("revenue by hour" should actually have a shape).
- **Session-level coherence.** A session's page views should cluster in a tight time window (minutes), not be scattered randomly across the day. Orders should occur *after* a plausible sequence of views and cart adds, with believable gaps (seconds to minutes), not before them.
- **Growth or seasonality trend, if you want extra realism.** A slow upward trend in daily volume mimics business growth and makes month-over-month mart metrics meaningful.

### 3.3 Messy and late data — the part that matters most

This is the single highest-leverage design decision in Week 1, because it's what justifies almost everything in Weeks 3–4 (dbt tests, Great Expectations, backfill handling). Without intentionally messy data, those steps have nothing to catch and look like busywork rather than engineering judgment.

Categories of messiness worth building in, deliberately and at a controlled *rate* (e.g., "2% of orders," "0.5% of events") so you can later report detection rates:

- **Late-arriving events.** An event's `event_time` (when it actually happened) should sometimes differ from its `ingested_time` (when it lands in the pipeline) by minutes, hours, or even a day. This is what you'll deliberately exercise in Week 4's "simulate a backfill" step — you need the generator to be capable of producing this on demand, not just accidentally.
- **Nulls in fields that shouldn't be null**, at a low rate — e.g., a missing `customer_id` on a guest checkout edge case, or a missing `product_id` due to a catalog sync issue. This is what your `not_null` dbt tests will actually catch.
- **Duplicate events.** Real event pipelines double-send sometimes (retries, at-least-once delivery). Emit occasional exact or near-exact duplicates so your `unique` dbt tests and dedup logic have something to do.
- **Referential inconsistency.** An order line item referencing a `product_id` that doesn't exist in your product dimension, or an event referencing a `session_id` that never had a corresponding page view. This is what `relationships` tests in dbt are designed to catch — build in the failure mode on purpose.
- **Type/format inconsistency**, e.g., a price field that's occasionally a string instead of a number, or a timestamp in a different format for a subset of records. This is a good one if you want your staging layer's "clean and type" step in Week 3 to have real work to do rather than being a no-op.
- **Out-of-order arrival.** Events for the same session shouldn't always arrive in event_time order — this matters once you're in Week 2's streaming step, since consumers need to handle events that arrive after later events from the same entity.

**Design tip:** make the messiness *configurable and seeded* (a fixed random seed, plus parameters for each anomaly rate). That gives you two things: reproducibility (you can regenerate the exact same "bad" dataset to demo a fix), and the ability to dial anomaly rates up for demo purposes when you want to show off a quality gate catching something in Week 4.

### 3.4 Volume and realism vs. practicality

You don't need "big data" volumes to make this project convincing — you need *shape*. A generator producing a few thousand events and a few hundred orders per simulated day, run over a simulated multi-week period, is enough to produce meaningful daily/weekly aggregates in your mart models, without making local iteration slow. Keep raw event volume high relative to order volume (real funnels are steep — most views don't convert), since that ratio itself becomes a metric you'll report on.

---

## 4. Landing Zone Design

The landing zone is where "raw, as-received" data lives — untransformed, immutable once written, exactly as it would look arriving from a real source system.

**Key principles, regardless of whether you implement with flat files or MinIO:**

- **Partition by date (and ideally by event type/source).** This is the pattern real data lakes use, and it's what lets Week 2's batch consumer, and Week 3's warehouse load, process data incrementally instead of re-reading everything. Decide now whether you partition by *event time* or *ingestion time* — and note in your README why. (Real systems usually partition by ingestion/arrival time for operational simplicity, while querying/business logic uses event time — this distinction is exactly what makes late-arriving data a genuine problem worth solving, not a contrived one.)
- **Immutability.** Once a raw file is written, it's never edited in place — corrections happen via new files (e.g., a late-arriving batch for a past date), never by mutating history. This is the principle that makes backfill in Week 4 well-defined rather than messy.
- **File format.** Raw/landing data is usually kept in a simple, self-describing, appendable format (e.g., line-delimited JSON) rather than a columnar format — columnar/compressed formats are typically an optimization applied at the *warehouse-load* stage (Week 3), not the landing stage. Keeping raw data in a simple format also makes it trivially inspectable when you're debugging.
- **Flat files vs. MinIO — think of this as a realism/effort tradeoff, not a right answer.** Flat files on disk get you moving fastest and are enough to prove the pipeline logic. MinIO (S3-compatible) more faithfully mirrors how a real ingestion pipeline lands data in cloud object storage, and pays off directly in Week 2 since your batch consumer will be writing to "S3" either way — if you start with MinIO now, Week 2 is a smaller step. If you start with flat files now, budget a bit of Week 2 time to migrate the writer.

---

## 5. What "done" looks like for Week 1

Before moving to Week 2, you should be able to answer yes to each of these:

- Can you regenerate the exact same dataset from scratch, deterministically (same seed → same output, including the same "bad" records in the same places)?
- Does the generator produce all three entity types (views, cart adds, orders) with a coherent funnel relationship between them?
- Have you verified, by eye, that timing patterns look realistic (plot event counts by hour and confirm it's not flat/uniform)?
- Does the generator produce each category of messiness (late arrivals, nulls, duplicates, referential breaks, type inconsistencies) at a known, adjustable rate?
- Is the landing zone partitioned in a way that would let you process "yesterday's data" without touching the rest?
- Have you started the README with the decisions above and your reasoning, not just the mechanics? (This is what turns "I built a pipeline" into "I can explain every tradeoff I made," which is the actual interview value of this project.)

---

## 6. How this sets up later weeks

Keeping this in mind now avoids rework:

- The messiness you build in Week 1 is *consumed* in Week 3 (dbt tests) and Week 4 (Great Expectations / quality gates, and the backfill simulation). If Week 1's generator can't produce late data and referential breaks on demand, Weeks 3–4 will feel unmotivated.
- The partitioning scheme you pick in Week 1 is what Week 2's consumer writes into and what Week 3's warehouse load reads from — get the date/event-type partitioning convention right once, and reuse it verbatim in later weeks rather than reinventing it.
- The entity/funnel model (view → cart add → order) is what makes "funnel conversion" a legitimate mart model in Week 3, rather than something bolted on later.

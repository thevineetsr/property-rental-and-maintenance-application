# Architecture & Design Decisions

A record of key tradeoffs made while building the system, why specific approaches were chosen, and what was changed along the way.

---

## 1. Cloud PostgreSQL on Supabase with SQLite Fallback

- **Decision**: Used Supabase (managed PostgreSQL) as the primary cloud database, but kept SQLite fully supported for local offline runs.
- **Why**: Supabase makes live cloud deployment simple with real-time table views and automated backups. At the same time, when running tests locally or reviewing code on a laptop without internet, nobody should be forced to spin up a PostgreSQL instance. SQLAlchemy makes it trivial to swap between them by changing `DATABASE_URL` in `.env`.
- **Lessons learned**: Direct connections to Supabase (`db.[ref].supabase.co`) use IPv6, which fails on some local Wi-Fi and university networks. We routed connections through Supabase's Supavisor connection pooler (`aws-0-[region].pooler.supabase.com:6543`) and added `?sslmode=require`, which works reliably across all networks.

---

## 2. Redacting Rent for Contractors via `None`

- **Decision**: Made `monthly_rent: Optional[Decimal] = None` in the `UnitResponse` schema so rent data returns as `None` whenever a contractor makes a request.
- **Why**: Requirement 1 mandates that contractors cannot see rent figures, and this must be enforced on the server. Returning `None` removes any ambiguity and keeps the API contract clean.
- **Change of plan**: I initially tried returning `Decimal("0.00")` for contractors, but Pydantic threw a validation error because the base schema had a strict `Field(gt=0)` check. Changing the response schema to `Optional[Decimal] = None` resolved the validation error cleanly and is much better semantics anyway (the field is redacted, not literally zero dollars).

---

## 3. Handling Lifecycle Transitions in Python Services (Not Database Triggers)

- **Decision**: Put the state machine rules (`Reported -> Triaged -> Scheduled -> Resolved`) in `maintenance_service.py` rather than using PostgreSQL triggers or frontend checks.
- **Why**:
  - Frontend checks can be bypassed by any direct API request or script.
  - Database triggers make debugging difficult, can't easily be unit-tested in pytest with SQLite, and return cryptic SQL errors to the frontend.
  - Writing the validation in pure Python allows returning descriptive HTTP 400 messages (e.g., *"Cannot schedule maintenance request because no contractor is assigned."*) and keeps unit tests fast.

---

## 4. Dedicated Append-Only Timeline Table (Not Heavy Event Sourcing)

- **Decision**: Built a simple `maintenance_timeline_events` table where every change appends a new row, with no `UPDATE` or `DELETE` endpoints.
- **Why**: Requirement 9 asks for a timeline you cannot rewrite. While full event-sourcing (like CQRS / Kafka) is popular in enterprise architectures, it adds massive complexity (event replay, read-model projections, eventual consistency). A standard relational table with append-only access gives 100% audit immutability, foreign-key integrity, and sub-millisecond query times.

---

## 5. Month-Scoped Dismissals for Rent Alerts

- **Decision**: Stored dismissed alerts in a `dismissed_rent_alerts` table keyed by `(unit_id, month_covered)`.
- **Why**: Requirement 10 says that if a manager dismisses an overdue alert for a unit, the alert must return if the tenant is still behind next month. A simple boolean like `is_alert_dismissed = True` on the `units` table would silence alerts forever. Keying dismissals by month means dismissing September's overdue alert won't hide an unpaid October balance.

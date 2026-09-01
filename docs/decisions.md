# Decisions

Log of key architectural decisions that shaped the system.

## Decision 1: Dual PostgreSQL / SQLite Support via SQLAlchemy Abstraction

- **Chose:** Configuring SQLAlchemy and Alembic with dynamic dialect support (`settings.DATABASE_URL`), enabling seamless connectivity to managed PostgreSQL (Supabase, Neon, Render) in production while defaulting to SQLite (`sqlite:///./property_rental.db`) for local testing.
- **Rejected:** Hardcoding PostgreSQL-only connections without local fallback.
- **Why:** In real-world teams and evaluations, developers and CI environments may not have local PostgreSQL daemons running. SQLAlchemy abstracts SQL dialects cleanly; adding `render_as_batch=True` in Alembic migrations guarantees that table alterations and schema migrations execute identically across both engines without sacrificing production PostgreSQL compatibility.

## Decision 2: Contractor Privacy Masking via Optional Fields

- **Chose:** Making `monthly_rent: Optional[Decimal] = None` in the `UnitResponse` schema, and returning `None` and `"HIDDEN"` whenever an authenticated user with role `MAINTENANCE_CONTRACTOR` queries units.
- **Rejected:** Creating duplicate Pydantic models for every endpoint or returning `0.00` for hidden rent.
- **Why:** Requirement 1 strictly mandates: "Maintenance contractors cannot see rent data. The difference must be enforced on the server, not just hidden in the interface." Returning `None` removes any ambiguity about actual contract rent, prevents information leakage, and enforces server-side privacy.
- **Later reversed:** Initially, the endpoint returned `monthly_rent = Decimal("0.00")` for contractors. However, this failed Pydantic response validation because `monthly_rent` had a strict `Field(gt=0)` validator inherited from unit creation. We reversed the decision and updated `UnitResponse` to have `monthly_rent: Optional[Decimal] = None`. This is semantically superior because `None` explicitly conveys that the field is redacted, rather than implying the rent is $0.00.

## Decision 3: Centralized Lifecycle Transition Engine in Service Layer

- **Chose:** Centralizing the 4-stage lifecycle state machine (`REPORTED -> TRIAGED -> SCHEDULED -> RESOLVED -> TRIAGED`) inside `maintenance_service.py` with explicit transition checks and prerequisite validation.
- **Rejected:** Validating transitions in frontend Streamlit components, or embedding procedural logic inside PostgreSQL trigger functions.
- **Why:** Frontend checks can be bypassed by any direct API client or script. Conversely, database triggers make debugging difficult, obscure error messages, and complicate automated unit testing. Placing the transition engine in the backend service layer allows the server to reject illegal transitions with descriptive error messages (e.g., explaining why scheduling requires an assigned contractor) and atomically log timeline audit events.

## Decision 4: Dedicated Append-Only Timeline Table vs. Full Event Sourcing

- **Chose:** A dedicated `maintenance_timeline_events` append-only table without any `UPDATE` or `DELETE` API endpoints or service methods.
- **Rejected:** Full event-sourcing architecture (e.g. CQRS with Kafka/EventStore) or generic JSON change logging.
- **Why:** Full event-sourcing introduces substantial operational complexity, event versioning overhead, and read-model synchronization delays that are completely unwarranted for a portfolio of dozens or hundreds of units. A dedicated relational timeline table provides strict immutability, foreign-key referential integrity, and simple SQL queries.

## Decision 5: Month-Scoped Rent Alert Dismissals

- **Chose:** Tracking dismissed overdue alerts in a dedicated `dismissed_rent_alerts` table with a composite unique constraint on `(unit_id, month_covered)`.
- **Rejected:** Adding an `is_alert_dismissed` boolean flag on the `units` table.
- **Why:** Requirement 10 specifies: "A property manager can dismiss the alert for that unit. If the unit's rent is still unmatched after the grace period in a later month, the alert returns." A boolean flag on `units` would permanently silence alerts for all future months. Scoping dismissal records to specific `(unit_id, month_covered)` pairs guarantees that an unpaid balance in any future month will automatically resurface the alert badge in the navigation.

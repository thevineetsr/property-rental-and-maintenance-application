# Database Schema Documentation

The database schema is implemented for PostgreSQL (hosted in production on Supabase, with full local SQLite fallback compatibility). All tables, constraints, foreign keys, and indexes are tracked and versioned via Alembic migrations.

## Table-by-Table Definitions

### 1. `users`
Stores user accounts for both property managers and maintenance contractors.

| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | `INTEGER` | `PRIMARY KEY`, Autoincrement | Unique internal user ID |
| `email` | `VARCHAR(255)` | `NOT NULL`, `UNIQUE`, Indexed | Login email (case-insensitive in business logic) |
| `password_hash` | `VARCHAR(255)` | `NOT NULL` | Salted bcrypt password hash |
| `full_name` | `VARCHAR(255)` | `NOT NULL` | Display name of the user |
| `role` | `VARCHAR(50)` | `NOT NULL` | Role: `PROPERTY_MANAGER` or `MAINTENANCE_CONTRACTOR` |
| `created_at` | `TIMESTAMP` | `NOT NULL`, Default UTC now | Registration timestamp |
| `updated_at` | `TIMESTAMP` | `NOT NULL`, Default UTC now | Last profile update timestamp |

### 2. `units`
Represents physical rental units in the property portfolio.

| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | `INTEGER` | `PRIMARY KEY`, Autoincrement | Unique unit ID |
| `unit_number` | `VARCHAR(50)` | `NOT NULL`, Indexed | Unit label (e.g. "101", "Penthouse A") |
| `address` | `VARCHAR(255)` | `NOT NULL` | street address |
| `monthly_rent` | `NUMERIC(10, 2)` | `NOT NULL`, Positive | Base monthly contract rent amount |
| `tenant_name` | `VARCHAR(255)` | `NULLABLE` | Current occupying tenant name; null if vacant |
| `archived` | `BOOLEAN` | `NOT NULL`, Default `FALSE`, Indexed | Soft-deletion flag preserving history |
| `created_at` | `TIMESTAMP` | `NOT NULL`, Default UTC now | Record creation timestamp |
| `updated_at` | `TIMESTAMP` | `NOT NULL`, Default UTC now | Record modification timestamp |

### 3. `rent_payments`
Stores recorded rent payments, each explicitly tagged with the month it covers.

| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | `INTEGER` | `PRIMARY KEY`, Autoincrement | Unique payment transaction ID |
| `unit_id` | `INTEGER` | `NOT NULL`, `FK(units.id ON DELETE CASCADE)`, Indexed | Associated unit |
| `amount` | `NUMERIC(10, 2)` | `NOT NULL`, Positive | Payment amount received |
| `month_covered` | `VARCHAR(7)` | `NOT NULL`, Indexed | Month covered in `YYYY-MM` format (e.g. `2026-09`) |
| `payment_date` | `TIMESTAMP` | `NOT NULL`, Default UTC now | Actual timestamp payment was received |
| `notes` | `VARCHAR(255)` | `NULLABLE` | Payment reference, check number, or bank note |
| `created_at` | `TIMESTAMP` | `NOT NULL`, Default UTC now | Audit timestamp when record was logged |

### 4. `maintenance_requests`
Tracks individual maintenance and repair issues.

| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | `INTEGER` | `PRIMARY KEY`, Autoincrement | Unique maintenance ticket number |
| `unit_id` | `INTEGER` | `NOT NULL`, `FK(units.id ON DELETE CASCADE)`, Indexed | Unit requiring maintenance |
| `description` | `TEXT` | `NOT NULL` | Full issue report description |
| `priority` | `VARCHAR(20)` | `NOT NULL`, Default `MEDIUM`, Indexed | `LOW`, `MEDIUM`, or `HIGH` |
| `status` | `VARCHAR(20)` | `NOT NULL`, Default `REPORTED`, Indexed | `REPORTED`, `TRIAGED`, `SCHEDULED`, or `RESOLVED` |
| `created_by_id` | `INTEGER` | `NOT NULL`, `FK(users.id)`, Indexed | User ID who reported the ticket |
| `created_at` | `TIMESTAMP` | `NOT NULL`, Default UTC now, Indexed | Timestamp ticket was opened |
| `updated_at` | `TIMESTAMP` | `NOT NULL`, Default UTC now | Last status or detail modification timestamp |

### 5. `maintenance_request_contractors` (Association Table)
Enforces a true many-to-many relationship between maintenance requests and assigned contractors.

| Column | Type | Constraints | Description |
|---|---|---|---|
| `maintenance_request_id` | `INTEGER` | `PRIMARY KEY`, `FK(maintenance_requests.id ON DELETE CASCADE)` | Maintenance request reference |
| `contractor_id` | `INTEGER` | `PRIMARY KEY`, `FK(users.id ON DELETE CASCADE)` | Contractor user reference |
| `assigned_at` | `TIMESTAMP` | `NOT NULL`, Default UTC now | Timestamp of assignment |

### 6. `maintenance_timeline_events`
An append-only, immutable audit log of every event that occurs on a maintenance ticket.

| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | `INTEGER` | `PRIMARY KEY`, Autoincrement | Event log ID |
| `maintenance_request_id` | `INTEGER` | `NOT NULL`, `FK(maintenance_requests.id ON DELETE CASCADE)`, Indexed | Associated ticket |
| `actor_id` | `INTEGER` | `NULLABLE`, `FK(users.id ON DELETE SET NULL)`, Indexed | User who triggered the action |
| `event_type` | `VARCHAR(50)` | `NOT NULL` | Event type (`CREATED`, `STATUS_CHANGED`, `CONTRACTOR_ASSIGNED`, `CONTRACTOR_UNASSIGNED`, `NOTE_ADDED`, `DETAILS_UPDATED`) |
| `old_value` | `VARCHAR(255)` | `NULLABLE` | Previous state/assignment |
| `new_value` | `VARCHAR(255)` | `NULLABLE` | Updated state/assignment |
| `note` | `TEXT` | `NULLABLE` | Human notes or explanation accompanying the event |
| `created_at` | `TIMESTAMP` | `NOT NULL`, Default UTC now | Immutable event timestamp |

### 7. `dismissed_rent_alerts`
Tracks manager dismissals of overdue rent alerts scoped specifically per unit and month.

| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | `INTEGER` | `PRIMARY KEY`, Autoincrement | Record ID |
| `unit_id` | `INTEGER` | `NOT NULL`, `FK(units.id ON DELETE CASCADE)`, Indexed | Unit whose alert was dismissed |
| `month_covered` | `VARCHAR(7)` | `NOT NULL`, Indexed | Scoped month (`YYYY-MM`) |
| `dismissed_by_id` | `INTEGER` | `NOT NULL`, `FK(users.id ON DELETE CASCADE)` | Manager who dismissed the alert |
| `dismissed_at` | `TIMESTAMP` | `NOT NULL`, Default UTC now | Dismissal timestamp |

*Composite Constraint*: `UNIQUE(unit_id, month_covered)` ensures an alert dismissed for August automatically returns if September rent is overdue.

---

## Entity Relationships

- **One-to-Many**:
  - `units` ➔ `rent_payments`: One unit can have numerous rent payments across months.
  - `units` ➔ `maintenance_requests`: One unit can have many maintenance requests.
  - `users` (manager/contractor) ➔ `maintenance_requests` (creator): One user creates multiple requests.
  - `maintenance_requests` ➔ `maintenance_timeline_events`: One ticket has an ordered stream of immutable audit events.
  - `units` ➔ `dismissed_rent_alerts`: One unit can have dismissed alert records across different months.
- **Many-to-Many**:
  - `maintenance_requests` ⇄ `users` (contractors): Linked via `maintenance_request_contractors`. A single ticket can have multiple contractors assigned (e.g. a plumber and an electrician), and a single contractor can be assigned to multiple tickets across different units.

---

## Constraints: Database vs. Application Code

### Database Enforced
- **Referential Integrity (`FOREIGN KEY ... ON DELETE CASCADE`)**: Deleting or archiving entities cannot leave orphan records in child tables.
- **Uniqueness (`UNIQUE(email)`)**: Guarantees no two users register with the same email.
- **Scoped Uniqueness (`UNIQUE(unit_id, month_covered)`)**: In `dismissed_rent_alerts`, prevents duplicate dismissals and guarantees alert return semantics in subsequent months.
- **Data Types & Non-Nullability (`NOT NULL`)**: Required fields (amounts, addresses, unit numbers, statuses) cannot be inserted as null.

### Application Code Enforced
- **Lifecycle Transition Rules**: The valid state graph (`REPORTED -> TRIAGED -> SCHEDULED -> RESOLVED -> TRIAGED`) is enforced by `maintenance_service.update_request_status`. Transition rules involve domain context and conditional rules (e.g. `len(assigned_contractors) >= 1`) that cannot be expressed via simple database constraints.
- **Role-Based Access Control**: Ensuring contractors cannot see rent amounts or access unassigned tickets is enforced in FastAPI dependencies and route queries.
- **Grace Period Calculation**: The 5-day grace period logic compares the calendar day against `due_date + 5 days` dynamically in code.
- **Soft-Delete Unique Unit Number**: Unit numbers must be unique among active units, but an archived historic unit may share a number with a restored unit once renamed.

---

## Deliberate Denormalization

- **Formatted `month_covered` (`VARCHAR(7)` e.g. `2026-09`)**: Rather than extracting year and month via SQL date functions on payment dates (which might differ from the month covered, e.g. an August 28th payment covering September), `month_covered` is stored directly as an indexed ISO string. This makes rent roll matching, grouping, and alert lookups fast and index-friendly.
- **Cached Display Metadata in Timelines (`old_value`, `new_value`)**: Historical status values are saved directly as text in the timeline event instead of referencing foreign keys. This guarantees the timeline is completely immutable even if users or contractors are modified.

---

## What Would Break First at 100x Data?

At 100x data (e.g., 5,000+ units, 100,000+ payments, 50,000+ maintenance requests):

1. **Unindexed Rent Roll Aggregations**:
   - `get_portfolio_rent_roll` currently queries `RentPayment` grouped by `unit_id` and `month_covered`. At 100x scale, scanning all payments dynamically would increase page load time.
   - *Remedy*: Add a composite index on `rent_payments(unit_id, month_covered, amount)` or maintain a materialized view of monthly balances.
2. **Weekly Resolved Maintenance Trend (Past 8 Weeks)**:
   - The dashboard currently computes resolved counts across 8 date ranges using individual query counts.
   - *Remedy*: Replace with a single SQL query using `GROUP BY date_trunc('week', created_at)` with an index on `maintenance_timeline_events(event_type, new_value, created_at)`.
3. **Database Connection Limits & Pooling**:
   - At high concurrent API traffic, direct PostgreSQL connections can saturate server limits.
   - *Remedy*: Connect through Supabase's managed connection pooler (Supavisor) in Session mode (`port 5432 / 6543`), configuring SQLAlchemy with `pool_size=20`, `max_overflow=10`, and `pool_pre_ping=True` to maintain resilient connection lifecycles without leaks.

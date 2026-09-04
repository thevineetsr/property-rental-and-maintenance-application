# AI Prompts Log

Notes on where I used AI tools during development, what code was generated, and the bugs or edge cases I had to catch and fix myself.

---

## 1. Initial Architecture & Specification Analysis

### Prompt
> "Analyze the takehome assignment requirements and produce a clean project structure for the Property Rental & Maintenance system using FastAPI, SQLAlchemy, Alembic, PostgreSQL/SQLite, and Streamlit."

### What was generated
- Initial breakdown of the 10 requirements.
- Suggested directory structure separating backend (`core`, `db`, `models`, `schemas`, `services`, `api`, `tests`) from frontend (`api_client`, `styles`, `views`).
- Basic SQLite and PostgreSQL dual setup.

### What I had to fix
- The generated plan didn't adequately address server-side contractor data privacy. I had to explicitly enforce data masking at the Pydantic serialization layer so contractors cannot see rent amounts even if they query units directly.

---

## 2. Maintenance Lifecycle Rules

### Prompt
> "Implement the maintenance request lifecycle transitions with strict rules: Reported -> Triaged -> Scheduled -> Resolved. Enforce that moving to Scheduled requires at least one assigned contractor, and reopening a Resolved ticket returns it to Triaged rather than Reported. Reject all other transitions with clear error messages."

### What was generated
- Basic `if/elif` state validation returning HTTP 400 errors.
- Contractor count check `len(request.assigned_contractors) >= 1`.
- Append-only timeline logging for status changes.

### What I had to fix
- The initial code allowed contractors to accidentally overwrite assigned contractors when updating descriptions. I separated contractor assignment permissions so only managers can touch the assignment list.

---

## 3. Contractor Rent Privacy (Validation Bug Fix)

### Prompt
> "Ensure that when a contractor calls GET /api/units, rent data is hidden. Return monthly_rent as 0.00 and rent_status as HIDDEN."

### What was generated
- Set `monthly_rent = Decimal("0.00")` when `current_user.role == "MAINTENANCE_CONTRACTOR"`.
- However, running pytest immediately crashed with a `ValidationError`: `monthly_rent: Input should be greater than 0` because `UnitResponse` had inherited `Field(gt=0)` from the unit creation schema.

### What I had to fix
- Changed `UnitResponse` to have `monthly_rent: Optional[Decimal] = None`.
- Updated the endpoints and tests to expect `None` instead of `0.00`. This fixed the validation crash and is much cleaner semantics (the rent is hidden, not free).

---

## 4. Bulk Rent Processing

### Prompt
> "Implement the bulk rent payment processor for a given month accepting unit identifiers and amounts. Classify each row into matched, underpaid, overpaid, or unmatched. Persist matched and partially paid payments in a database transaction."

### What was generated
- `process_bulk_rent` function matching units by ID or number.
- Classification logic comparing amounts against `unit.monthly_rent`.

### What I had to fix
- Bulk CSV files often have subtle trailing whitespace or casing differences (e.g., `"101 "` vs `"101"`). I added `.strip()` and case-insensitive matching (`u.unit_number.lower()`) so real-world bank exports don't fail to match.

---

## 5. Streamlit Frontend UI

### Prompt
> "Build Streamlit UI views for Property Manager and Maintenance Contractor. Include 1-click demo login buttons, KPI metric cards, status badges, overdue alerts count badge in navigation, and an immutable timeline display."

### What was generated
- Streamlit application structure with `api_client.py`.
- Form layouts, metric card containers, and status pills.

### What I had to fix
- On Windows terminal consoles (cp1252), raw Unicode emojis in console print statements crashed the seeding script. Replaced them with standard ASCII log indicators.
- Added custom CSS to give the timeline feed a clean, professional SaaS look.

---

## 6. Supabase Cloud Database Integration

### Prompt
> "Transition database persistence from local SQLite to managed cloud PostgreSQL on Supabase. Configure connection pooling via Supavisor, enforce SSL (sslmode=require), and ensure migration compatibility across both engines."

### What was generated
- PostgreSQL configuration using `psycopg2-binary` and dynamic `DATABASE_URL` loading.
- Alembic migration scripts applied directly to Supabase.

### What I had to fix
- Direct Supabase hostnames (`db.[ref].supabase.co`) resolve only to IPv6, which failed on campus/local networks with `could not translate host name: Name or service not known`. Fixed this by routing through Supabase's IPv4 connection pooler (`aws-0-[region].pooler.supabase.com:6543`).
- Added `?sslmode=require` to prevent Supabase from dropping connections during bulk seeding.

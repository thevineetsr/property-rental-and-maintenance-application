# AI Prompts Log

Chronological log of AI prompts used during development, what was generated, and corrections made.

---

## 1. Initial Architecture & Specification Analysis

### Prompt
> "Analyze the takehome assignment requirements and produce a production-quality implementation plan for the Property Rental & Maintenance Management System adhering to all 10 requirements using FastAPI, SQLAlchemy, Alembic, PostgreSQL/SQLite, and Streamlit."

### What you got
- A breakdown of the 10 requirements.
- Proposed directory structure separating backend (core, db, models, schemas, services, api, tests) from frontend (api_client, styles, views).
- Identified the need for dual database support (PostgreSQL for cloud/production and SQLite for local development).

### What you corrected
- Added explicit clarification that contractor data privacy must be enforced at the API response serialization layer, ensuring contractors can never retrieve rent amounts or status even when querying units or individual endpoints directly.

---

## 2. Maintenance Lifecycle Engine & State Validation

### Prompt
> "Implement the maintenance request lifecycle transitions with strict rules: Reported -> Triaged -> Scheduled -> Resolved. Enforce that moving to Scheduled requires at least one assigned contractor, and reopening a Resolved ticket returns it to Triaged rather than Reported. Reject all other transitions with clear error messages."

### What you got
- Service logic checking `current_status` and `new_status` with `if/elif` branches and raising `HTTPException(400, detail=...)`.
- Prerequisite check verifying `len(request.assigned_contractors) >= 1`.
- Append-only logging to `maintenance_timeline_events`.

### What you corrected
- Ensured that when contractors edit request details (description/priority), contractor assignment remains strictly untouched and cannot be modified through the update endpoint.

---

## 3. Contractor Privacy & Unit Response Schema (Error & Correction)

### Prompt
> "Ensure that when a contractor calls GET /api/units, rent data is hidden. Return monthly_rent as 0.00 and rent_status as HIDDEN."

### What you got
- Implemented `monthly_rent = Decimal("0.00")` when `current_user.role == "MAINTENANCE_CONTRACTOR"`.
- However, during automated test runs (`pytest backend/tests/test_units.py`), this produced a `pydantic_core.ValidationError`: `monthly_rent: Input should be greater than 0 [type=greater_than, input_value=Decimal('0.00')]` because `UnitResponse` inherited `Field(gt=0)` from `UnitBase`.

### What you corrected
- Modified `UnitResponse` to have `monthly_rent: Optional[Decimal] = None`.
- Updated `list_units` and `get_unit` to assign `monthly_rent = None` when accessed by contractors.
- Updated unit tests to assert `u["monthly_rent"] is None`. This resolved the validation error and provided clearer semantics (the value is omitted/redacted, not literally $0).

---

## 4. Bulk Rent Processing & Classification Engine

### Prompt
> "Implement the bulk rent payment processor for a given month accepting unit identifiers and amounts. Classify each row into matched, underpaid, overpaid, or unmatched. Persist matched and partially paid payments in a database transaction."

### What you got
- `process_bulk_rent` service function matching units by unit number or unit ID.
- Classification logic comparing received amount against `unit.monthly_rent`.
- Generation of `RentPayment` records.

### What you corrected
- Ensured case-insensitive matching on unit identifiers (`u.unit_number.lower()`) so whitespace and casing variations in bulk bank exports (e.g. `101 ` vs `101`) match successfully.

---

## 5. Streamlit Frontend UI & Interactive Timeline

### Prompt
> "Build Streamlit UI views for Property Manager and Maintenance Contractor. Include 1-click demo login buttons, KPI metric cards, status badges, overdue alerts count badge in navigation, and an immutable timeline display."

### What you got
- Complete Streamlit application with `api_client.py` sending authenticated HTTP requests.
- Custom CSS badges and timeline container tokens.
- Role-based routing separating Manager views from Contractor workspace.

### What you corrected
- Addressed Windows cp1252 console encoding issues in seed script by replacing raw unicode emojis with clean ASCII indicators.

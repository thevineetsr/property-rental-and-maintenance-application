# Submission

## Links

- **GitHub repository:** <public repo URL>
- **Live application:** <deployed URL>

## Notes for the reviewer

A few practical pointers to help you navigate and test the project:

- **Quick Login**: On the login screen, you don't need to manually type credentials — just click any of the **Quick Login** buttons to immediately test as the Property Manager or as either of the two Maintenance Contractors.
- **Interactive API Docs**: FastAPI's Swagger docs are available at `/docs` (or `http://127.0.0.1:8000/docs` locally) where you can interactively test all routes, schema validations, and role restrictions.
- **Running Locally**:
  - Backend: `python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload`
  - Frontend: `python -m streamlit run frontend/app.py --server.port 8501`
  - Automated tests: `python -m pytest backend/tests/ -v` (23 tests covering auth, roles, lifecycle transitions, bulk rent, and timeline immutability).
  - Re-seed demo data: `python -m backend.app.seed`
- **Database Flexibility**: The app connects to cloud PostgreSQL on Supabase by default (with SSL and connection pooling), but you can also swap `DATABASE_URL` in `.env` to SQLite (`sqlite:///./property_rental.db`) for a completely offline, zero-setup run.

## Demo credentials

| Role | Email | Password | What this role can do |
|------|-------|----------|----------------------|
| **Property Manager** | `manager@property.com` | `Manager123!` | Full portfolio access: view rent roll, process bulk payments, assign contractors, edit units. |
| **Contractor (Plumbing/HVAC)** | `bob@contractor.com` | `Contractor123!` | Sees only plumbing/HVAC tickets assigned to him. Rent data is completely redacted. |
| **Contractor (Electrical)** | `alice@contractor.com` | `Contractor123!` | Sees only electrical tickets assigned to her. Cannot view or assign other contractors. |

## Stack

| Layer | What I used | Why |
|---|---|---|
| **Frontend** | Streamlit + Custom CSS | Allowed me to build the manager dashboard, ticket inspector, and bulk rent tools quickly in Python. Added custom CSS for clean metric cards, status tags, and timeline feeds so it looks like a real SaaS product. |
| **Backend** | FastAPI + Pydantic v2 | Keeps request validation and serialization strict. Role checks are handled cleanly via reusable FastAPI dependencies (`require_role`), and Swagger UI comes out of the box. |
| **Database** | PostgreSQL (Supabase) / SQLite | Supabase PostgreSQL gives reliable cloud persistence with foreign keys and indexes. Also kept SQLite compatibility so anyone running the code locally can boot it up in 10 seconds without cloud dependencies. |
| **ORM** | SQLAlchemy 2.0 | Clean query building, explicit relationship loading, and automatic session cleanup per request. |
| **Migrations** | Alembic | Keeps database changes versioned and reproducible across both PostgreSQL and SQLite. |
| **Authentication** | PyJWT + Bcrypt | Standard stateless Bearer tokens with salted bcrypt password hashing. |

## Goal checklist

| # | Goal | Status | Implementation details |
|---|------|--------|------------------------|
| 1 | Accounts and roles | Done | Enforced on the backend via route dependencies. If a contractor hits manager routes (rent, creating units, assigning staff), the server throws a 403. Rent fields are completely hidden (`None`) from contractors in unit responses. |
| 2 | Units | Done | Includes unit number, address, monthly rent, and tenant name. Built soft-delete archiving and restoring so past history is preserved. A 5-day grace period is factored into overdue calculations. |
| 3 | Maintenance requests | Done | M:N relationship between tickets and contractors. Both managers and contractors can create requests and tweak descriptions or priority, but only managers can assign/unassign workers. |
| 4 | Maintenance request lifecycle with rules | Done | Finite state machine: `REPORTED -> TRIAGED -> SCHEDULED -> RESOLVED`. The API will reject moving to `SCHEDULED` if no contractor is assigned yet. Reopening a resolved ticket returns it to `TRIAGED` (not `REPORTED`). |
| 5 | Assignment | Done | Multiple contractors can work on a single request, and contractors can juggle multiple requests. Contractors only see tickets assigned to their account across all units. |
| 6 | Finding requests | Done | Search by text, filter by status, priority, unit, and contractor, with sorting and pagination. All filtering and pagination logic runs in SQL queries on the backend, not in the browser. |
| 7 | Acting on rent for many units at once | Done | Bulk endpoint takes an array of unit IDs/amounts and classifies each as matched, underpaid, overpaid, or unmatched. There is also a one-click CSV export for the full portfolio rent roll. |
| 8 | A dashboard | Done | Shows key portfolio stats (collected rent, overdue count, open repairs), breakdown charts by status and contractor, an 8-week resolution trend chart, and a table flagging requests unattended for over 14 days. |
| 9 | History you cannot rewrite | Done | Dedicated append-only `maintenance_timeline_events` table that logs creation, every status transition (with old and new values), contractor assignments, and notes. No edit or delete endpoints exist for this table. |
| 10 | Rent alerts | Done | Unpaid units past the 5-day grace period trigger an alert and a count badge in the navigation. Dismissing is recorded per `(unit_id, month_covered)`, so if the tenant fails to pay again next month, the alert automatically reappears. |

## How much time did you actually spend?

Around **11.5 hours** total over 2 days:
- ~2.5 hours on data modeling, foreign keys, Alembic migration setup, and Supabase connection
- ~4 hours on backend services (lifecycle state machine, bulk rent classifier, timeline logging) and writing the 23 automated pytest cases
- ~3.5 hours on Streamlit views, API client integration, and custom CSS styling
- ~1.5 hours on edge-case testing, seed data, and documentation

## What would you do next, with another 12 hours?

1. **Photo and receipt uploads**: Add image attachments to maintenance tickets so tenants/contractors can take photos of damaged equipment, stored using Supabase Storage or S3.
2. **Automated notifications**: Send webhook or email/SMS alerts (via Resend or Twilio) when a ticket is assigned or when rent passes the grace period.
3. **Tenant-facing portal**: Give tenants a lightweight portal where they can check their balance, pay rent via Stripe, and view update logs on their repair requests.
4. **Better bulk import UX**: Add a drag-and-drop CSV preview table with validation warnings before confirming the bulk rent batch.

## What are you least happy with in this codebase, and why?

In `rent_service.py`, calculating whether each unit is paid up for the current month is done by pulling the unit's payments and computing the net balance in Python. While this is clean, easy to read, and fast for a portfolio of dozens of units, at 10,000+ units it would hammer the database with too many roundtrips.

Given more time, I would refactor that into a single SQL query with a `GROUP BY` and window function, or maintain a pre-calculated monthly ledger summary table.

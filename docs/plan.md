# Implementation Plan & Build Record

## How I Broke Down the Work

I divided the build into 6 practical phases over two days:

1. **Phase 1: Project Setup & Database Schema**
   - Configured the Python environment, dependencies (`requirements.txt`), and `.env` setup.
   - Defined SQLAlchemy models for all 7 entities: `User`, `Unit`, `RentPayment`, `MaintenanceRequest`, `MaintenanceRequestContractor`, `MaintenanceTimelineEvent`, and `DismissedRentAlert`.
   - Set up Alembic migrations configured to run against both cloud Supabase PostgreSQL and local SQLite.
   - Implemented password hashing (bcrypt) and JWT auth helpers.

2. **Phase 2: Core Domain Services & Business Logic**
   - Wrote `unit_service` with archive/restore logic.
   - Built `rent_service` with the 5-day grace period check, CSV rent roll generator, and bulk payment matching (`matched`, `underpaid`, `overpaid`, `unmatched`).
   - Built `maintenance_service` with the strict 4-step state machine (`Reported -> Triaged -> Scheduled -> Resolved`), checking that a contractor is assigned before scheduling.
   - Built `dashboard_service` to compute headline KPIs and the 8-week resolution trend chart.

3. **Phase 3: FastAPI REST Endpoints & Role Checks**
   - Built routers for `/auth`, `/units`, `/rent`, `/maintenance`, and `/dashboard`.
   - Added `require_role` dependencies so contractors get an HTTP 403 on manager-only routes.
   - Implemented server-side search, filtering, sorting, and pagination on maintenance requests.

4. **Phase 4: Seed Data & Test Suite**
   - Created `backend/app/seed.py` with multi-month demo data, active/archived units, payments, and sample repair tickets.
   - Wrote 23 automated tests with pytest covering auth, unit management, contractor isolation, bulk rent classification, and timeline immutability (100% passing).

5. **Phase 5: Streamlit Frontend**
   - Built `frontend/api_client.py` so the UI communicates strictly via HTTP requests.
   - Added custom CSS for clean metric cards, status pills, and timeline feeds.
   - Built views for login (with 1-click demo buttons), Manager Dashboard, Units, Rent Roll & Bulk Payments, Ticket Inspector, and Contractor Workspace.

6. **Phase 6: Testing, Polish & Documentation**
   - Verified end-to-end flows locally and on Supabase.
   - Documented architecture, schema, trade-offs, and prompt history.

---

## Build Order: Why Backend-First?

I chose a **backend-first, dependencies-inward** approach:

1. **Database Schema first**: In property management, everything links together (units to payments, tickets to contractors and timeline logs). Getting the database schema right from day one avoided annoying schema refactors later.
2. **Business Services second**: Writing pure Python functions for business rules (grace periods, state machine moves) let me verify logic before wiring up web endpoints.
3. **FastAPI Endpoints third**: Exposing clean REST routes with Pydantic validation and HTTP error codes (400, 403, 404).
4. **Automated Tests fourth**: Having 23 automated tests gave me confidence that role boundaries and lifecycle rules were solid before touching the frontend.
5. **Streamlit UI fifth**: Because the API was already tested and working, hooking up the Streamlit UI was fast and painless.

---

## Time Estimates vs. Actuals

| Area | Estimated | Actual | Notes |
|---|---|---|---|
| Project setup & Alembic | 1.0 hr | 0.8 hr | Quick setup with standard Alembic patterns |
| Models & Schema Migrations | 1.5 hrs | 1.2 hrs | Smooth migration autogeneration |
| Domain Services & Lifecycle Engine | 2.5 hrs | 2.2 hrs | Transition edge cases cleanly organized in service files |
| FastAPI Routes & Role Security | 2.0 hrs | 1.8 hrs | FastAPI dependency injection made role checks simple |
| Automated Pytest Suite | 2.0 hrs | 1.5 hrs | 23 tests verifying all 10 core requirements |
| Streamlit UI & Styling | 2.5 hrs | 2.8 hrs | Took extra time polishing custom CSS badges and timeline feeds |
| Documentation & Live Verification | 1.5 hrs | 1.2 hrs | Cleaned up docs, tested Supabase connection |
| **Total** | **13.0 hrs** | **11.5 hrs** | Finished comfortably within budget |

---

## What I Chose to Cut to Stay on Schedule

1. **Email / SMS Notifications (SendGrid/Twilio)**:
   - Instead of spending time setting up third-party mail accounts, I focused on prominent in-app overdue alert badges and dashboard banners.
2. **Multi-Portfolio Partitioning**:
   - Left as a future stretch goal so all time went into making the 10 core requirements bulletproof.
3. **Drag-and-Drop Kanban Board**:
   - Streamlit doesn't support drag-and-drop kanban boards natively without external React components. A clean dropdown status selector with backend validation and immediate timeline updates was much more reliable.

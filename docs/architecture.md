# Architecture

## System Overview & Moving Pieces

I split the system into five straightforward layers so the backend logic stays completely isolated from the user interface:

1. **Frontend (Streamlit)**:
   - Provides role-tailored interfaces for Property Managers and Maintenance Contractors.
   - Stores only session state (`token`, `user`) in memory.
   - Has zero direct database access. Every button click, search, and form submission sends an HTTP request through `ApiClient` to the backend.

2. **API & Routing (FastAPI)**:
   - Exposes REST endpoints grouped under `/api` (`/auth`, `/units`, `/rent`, `/maintenance`, `/dashboard`).
   - Uses Pydantic for request and response validation, with Swagger docs auto-generated at `/docs`.
   - Enforces authentication and role checks (`require_role`) before invoking any business services.

3. **Domain Services & Business Logic**:
   - Holds all the actual business rules so they're never tied to the UI:
     - The 4-step maintenance ticket lifecycle (`Reported -> Triaged -> Scheduled -> Resolved`) and the rule requiring at least one assigned contractor before scheduling.
     - The 5-day grace period overdue check for rent payments.
     - Bulk rent matching and classification (`matched`, `underpaid`, `overpaid`, `unmatched`).
     - Writing immutable audit events into the maintenance timeline.

4. **Database Access (SQLAlchemy 2.0 & Alembic)**:
   - Handles SQL queries, entity relationships, and connection lifecycles.
   - Alembic manages schema migrations automatically, so updating tables is tracked and repeatable.

5. **Persistence Layer (Supabase PostgreSQL / SQLite)**:
   - In production/cloud, it runs on Supabase (managed PostgreSQL) with SSL and connection pooling.
   - Also supports local SQLite (`property_rental.db`) via `.env` for zero-setup offline testing.

```
+-------------------------------------------------------------+
|                     Streamlit UI                            |
|  (Manager Dashboard, Units Portfolio, Rent Roll, Workspace) |
+------------------------------+------------------------------+
                               | HTTPS / JSON (Bearer JWT)
+------------------------------v------------------------------+
|                     FastAPI Backend                         |
|  Dependencies: JWT Auth, require_role(PROPERTY_MANAGER)     |
+------------------------------+------------------------------+
                               |
+------------------------------v------------------------------+
|                 Domain Services Layer                       |
|  (unit_service, rent_service, maintenance_service)          |
+------------------------------+------------------------------+
                               | Transactions & Queries
+------------------------------v------------------------------+
|                   SQLAlchemy 2.0 ORM                        |
+------------------------------+------------------------------+
                               | SQL
+------------------------------v------------------------------+
|             PostgreSQL (Supabase) / SQLite DB               |
+-------------------------------------------------------------+
```

## Runtime Topology

- **Browser**: The user's web browser rendering Streamlit pages.
- **Frontend Server**: Python process running Streamlit (port `8501`).
- **Backend API**: Python process running FastAPI with Uvicorn (port `8000`).
- **Database**: Cloud PostgreSQL hosted on Supabase (or local SQLite file for offline dev).

## Request Flow Example: Scheduling a Repair Ticket

Here is how data flows through the stack when a Property Manager changes a maintenance request from `TRIAGED` to `SCHEDULED`:

1. **User Action**: The manager selects `SCHEDULED` from the status dropdown on a ticket and clicks "Update Status".
2. **Frontend Dispatch**: Streamlit calls `ApiClient.update_maintenance_status(request_id=1, status="SCHEDULED", note="Plumber booked")`. This sends a `PATCH /api/maintenance/1/status` with `Authorization: Bearer <token>`.
3. **Auth Check**: FastAPI's `require_authenticated` dependency validates the JWT signature and extracts the current user.
4. **Rule Enforcement**:
   - The route handler calls `maintenance_service.update_request_status(...)`.
   - The service loads the ticket from the DB and checks the transition rules:
     - Is it currently `TRIAGED`? Yes.
     - Is the next state `SCHEDULED`? Yes.
     - **Prerequisite Check**: Does it have at least one contractor assigned? If `len(assigned_contractors) == 0`, the service stops immediately and returns an HTTP 400: *"Cannot schedule maintenance request because no contractor is assigned."*
5. **State Update & Timeline Logging**:
   - If a contractor is assigned, `request.status` changes to `SCHEDULED`.
   - An event is appended to `maintenance_timeline_events` with `old_value="TRIAGED"`, `new_value="SCHEDULED"`, and the note.
   - The database transaction commits.
6. **UI Refresh**: The API returns the updated ticket data (HTTP 200), and Streamlit shows a success message while re-rendering the timeline.

## Things I Deliberately Chose Not to Build

1. **Background Job Queue (Celery/Redis)**:
   - For a portfolio of a few dozen to a few hundred units, queries run in under 20ms. Adding Redis and Celery would just mean more processes to monitor with no real benefit.
2. **Full React/Next.js SPA**:
   - The take-home emphasized developer velocity and clean Python integration. Streamlit allowed me to build interactive charts, filters, and forms rapidly without writing duplicate frontend models or build pipelines.
3. **Hard Deletes**:
   - In property management, you never delete financial or repair history. Everything uses soft-deleting (`archived = True`) and immutable timeline logs so you can always see past records.

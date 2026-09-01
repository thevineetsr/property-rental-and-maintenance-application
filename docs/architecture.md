# Architecture

## Moving Pieces & Communication

The system consists of five distinct, decoupled layers:

1. **Frontend Presentation Layer (Streamlit)**:
   - Provides role-tailored reactive user interfaces for Property Managers and Maintenance Contractors.
   - Maintains client session state (`token`, `user`) exclusively in memory.
   - Enforces zero direct database access; every view and action dispatches HTTP requests via `ApiClient`.

2. **API & Routing Layer (FastAPI)**:
   - Exposes RESTful endpoints organized under `/api` (`/auth`, `/units`, `/rent`, `/maintenance`, `/dashboard`).
   - Handles CORS middleware, OpenAPI/Swagger automated schema generation, and request parsing with Pydantic.
   - Enforces authentication and authorization dependencies (`get_current_user`, `require_role`) before invoking business logic.

3. **Domain Service & Business Logic Layer**:
   - Centralizes all domain rules:
     - Strict 4-step maintenance lifecycle transitions (`Reported -> Triaged -> Scheduled -> Resolved -> Triaged`) and checks that contractor assignment precedes scheduling.
     - Grace period overdue calculations (5-day window).
     - Atomic bulk rent matching and classification algorithms (`matched`, `underpaid`, `overpaid`, `unmatched`).
     - Immutable event timeline recording.
   - Guarantees that business integrity is completely independent of the frontend.

4. **Object-Relational Mapping & Database Abstraction (SQLAlchemy 2.0 & Alembic)**:
   - Manages relational mapping, entity relationships, query compilation, indexes, and session lifecycle (`get_db`).
   - Alembic tracks versioned schema migrations with repeatable migration scripts.

5. **Persistence Layer (PostgreSQL / SQLite)**:
   - Relational database storing users, units, rent payments, maintenance requests, contractor associations, timeline events, and alert dismissals.
   - Configured to run PostgreSQL in cloud/production and SQLite for local environments.

```
+-------------------------------------------------------------+
|                     Streamlit UI                            |
|  (Manager Dashboard, Units Portfolio, Rent Roll, Workspace) |
+------------------------------+------------------------------+
                               | HTTPS / JSON (Bearer JWT)
+------------------------------v------------------------------+
|                     FastAPI Gateway                         |
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
                               | Dialect SQL
+------------------------------v------------------------------+
|                 PostgreSQL / SQLite DB                      |
+-------------------------------------------------------------+
```

## Runtime Topology

- **Browser / Client**: Web browser rendering the Streamlit interface.
- **Frontend Server**: Python process running Streamlit (`localhost:8501` locally, or Vercel/Render/Streamlit Community Cloud).
- **Backend API Server**: ASGI process running FastAPI with Uvicorn (`localhost:8000` locally, or Render/Fly.io/Koyeb).
- **Database Server**: PostgreSQL database instance (e.g. Supabase, Neon, or local SQLite).

## Representative Request Path: Scheduling a Maintenance Request End to End

To illustrate how data and rules flow through the architecture, consider the action when a Property Manager transitions a maintenance request from `TRIAGED` to `SCHEDULED`:

1. **User Action**: The manager selects `SCHEDULED` in the status dropdown on the Maintenance Request page and clicks "Update Status".
2. **Frontend Dispatch**: Streamlit invokes `ApiClient.update_maintenance_status(request_id=1, status="SCHEDULED", note="On-site repair booked")`. This sends a `PATCH /api/maintenance/1/status` request with header `Authorization: Bearer <jwt_token>`.
3. **Authentication & Authorization**:
   - FastAPI intercepts the request. The `require_authenticated` dependency extracts the Bearer token from the `Authorization` header.
   - `decode_access_token` verifies the cryptographic signature and token expiry. The user record is retrieved from the database.
4. **Service Execution & Rule Enforcement**:
   - The route handler invokes `maintenance_service.update_request_status(db, request_id, status_data, current_user)`.
   - The service fetches the maintenance request and validates the state transition:
     - Current state must be `TRIAGED`.
     - Target state is `SCHEDULED`.
     - **Constraint Check**: `len(request.assigned_contractors) >= 1`. If zero contractors are assigned, the service immediately halts execution and raises `HTTPException(400, "Cannot schedule maintenance request because no contractor is assigned.")`.
5. **State Mutation & Immutable Timeline Logging**:
   - If at least one contractor is assigned, `request.status` is updated to `SCHEDULED`.
   - The service calls `log_timeline_event(db, request_id=1, event_type=TimelineEventType.STATUS_CHANGED, actor_id=manager.id, old_value="TRIAGED", new_value="SCHEDULED", note="On-site repair booked")`.
   - The database transaction commits atomically.
6. **Response & UI Refresh**:
   - The API returns HTTP 200 with the serialized `MaintenanceRequestResponse` DTO.
   - Streamlit receives the response, shows a success toast, and refreshes the timeline and badges.

## What We Deliberately Decided NOT to Build

1. **Asynchronous Background Task Queue (Celery / RabbitMQ / Redis)**:
   - *Rationale*: For a portfolio of dozens to hundreds of units, bulk rent matching and CSV roll generation execute in sub-millisecond database queries. Adding Redis and Celery workers would introduce significant operational overhead and infrastructure complexity with zero practical benefit.
2. **Full Client-Side Single Page App (React / Vue / Next.js)**:
   - *Rationale*: The specification prioritized Streamlit for rapid iteration, clean UI, and direct pairing with Python data visualization components. By strictly decoupling Streamlit from business logic and routing all operations through a RESTful FastAPI backend, we achieved clean separation of concerns without the boilerplate of a separate JS/Node build toolchain.
3. **Hard Deletion Endpoints for Units or Maintenance Records**:
   - *Rationale*: In property management, financial and maintenance audits require preserving historical records indefinitely. Soft-deletion via `archived = True` and immutable timeline event logging ensure historical integrity is never compromised.

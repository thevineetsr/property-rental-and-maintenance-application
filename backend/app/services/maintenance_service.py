from datetime import datetime, timezone
from typing import List, Optional, Tuple, Any
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import or_, desc, asc, func
from fastapi import HTTPException, status
from backend.app.models.user import User, UserRole
from backend.app.models.unit import Unit
from backend.app.models.maintenance import (
    MaintenanceRequest,
    MaintenancePriority,
    MaintenanceStatus,
    maintenance_request_contractors,
)
from backend.app.models.timeline import MaintenanceTimelineEvent, TimelineEventType
from backend.app.schemas.maintenance import (
    MaintenanceRequestCreate,
    MaintenanceRequestUpdate,
    MaintenanceStatusUpdate,
    MaintenanceRequestResponse,
    ContractorSummary,
    TimelineEventResponse,
)


def log_timeline_event(
    db: Session,
    request_id: int,
    event_type: TimelineEventType,
    actor_id: Optional[int] = None,
    old_value: Optional[str] = None,
    new_value: Optional[str] = None,
    note: Optional[str] = None
) -> MaintenanceTimelineEvent:
    """Create an immutable timeline event."""
    event = MaintenanceTimelineEvent(
        maintenance_request_id=request_id,
        actor_id=actor_id,
        event_type=event_type.value,
        old_value=old_value,
        new_value=new_value,
        note=note,
        created_at=datetime.now(timezone.utc)
    )
    db.add(event)
    return event


def create_maintenance_request(
    db: Session,
    data: MaintenanceRequestCreate,
    creator: User
) -> MaintenanceRequest:
    """Create a new maintenance request in REPORTED status."""
    unit = db.query(Unit).filter(Unit.id == data.unit_id).first()
    if not unit:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Unit with ID {data.unit_id} not found."
        )

    request = MaintenanceRequest(
        unit_id=data.unit_id,
        description=data.description.strip(),
        priority=data.priority.value,
        status=MaintenanceStatus.REPORTED.value,
        created_by_id=creator.id,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )
    db.add(request)
    db.flush()  # assign request.id

    # Log timeline creation event
    log_timeline_event(
        db=db,
        request_id=request.id,
        event_type=TimelineEventType.CREATED,
        actor_id=creator.id,
        new_value=MaintenanceStatus.REPORTED.value,
        note=f"Created with {data.priority.value} priority: {data.description[:100]}"
    )

    db.commit()
    db.refresh(request)
    return request


def get_request_by_id(
    db: Session,
    request_id: int,
    viewer: User
) -> MaintenanceRequest:
    """
    Retrieve request by ID with role-based access validation.
    Contractors can only access requests assigned to them.
    """
    request = db.query(MaintenanceRequest).filter(
        MaintenanceRequest.id == request_id
    ).first()

    if not request:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Maintenance request #{request_id} not found."
        )

    # Authorization check for contractors
    if viewer.role == UserRole.MAINTENANCE_CONTRACTOR.value:
        assigned_ids = [c.id for c in request.assigned_contractors]
        if viewer.id not in assigned_ids:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: You are not assigned to this maintenance request."
            )

    return request


def update_request_details(
    db: Session,
    request_id: int,
    data: MaintenanceRequestUpdate,
    actor: User
) -> MaintenanceRequest:
    """Edit description and/or priority. Can be done by manager or assigned contractor."""
    request = get_request_by_id(db, request_id, actor)

    changes = []
    if data.description is not None and data.description.strip() != request.description:
        request.description = data.description.strip()
        changes.append("description updated")

    if data.priority is not None and data.priority.value != request.priority:
        old_pri = request.priority
        request.priority = data.priority.value
        changes.append(f"priority changed from {old_pri} to {data.priority.value}")

    if changes:
        request.updated_at = datetime.now(timezone.utc)
        log_timeline_event(
            db=db,
            request_id=request.id,
            event_type=TimelineEventType.DETAILS_UPDATED,
            actor_id=actor.id,
            note="; ".join(changes)
        )
        db.commit()
        db.refresh(request)

    return request


def update_request_status(
    db: Session,
    request_id: int,
    status_data: MaintenanceStatusUpdate,
    actor: User
) -> MaintenanceRequest:
    """
    Validate and execute maintenance request lifecycle transitions.
    
    Lifecycle rules:
    - REPORTED -> TRIAGED
    - TRIAGED -> SCHEDULED (Requires >= 1 assigned contractor)
    - SCHEDULED -> RESOLVED
    - RESOLVED -> TRIAGED (Reopening returns to TRIAGED)
    All other transitions are rejected with descriptive messages.
    """
    request = get_request_by_id(db, request_id, actor)
    current_status = request.status
    new_status = status_data.status.value

    if current_status == new_status:
        return request

    # Validate lifecycle transition rules
    if current_status == MaintenanceStatus.REPORTED.value:
        if new_status != MaintenanceStatus.TRIAGED.value:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"Invalid status transition from {current_status} to {new_status}. "
                    "A reported request must first move to TRIAGED."
                )
            )

    elif current_status == MaintenanceStatus.TRIAGED.value:
        if new_status != MaintenanceStatus.SCHEDULED.value:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"Invalid status transition from {current_status} to {new_status}. "
                    "A triaged request can only move to SCHEDULED."
                )
            )
        # CRITICAL RULE: Cannot move from TRIAGED to SCHEDULED unless at least one contractor is assigned!
        if len(request.assigned_contractors) == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot schedule maintenance request because no contractor is assigned."
            )

    elif current_status == MaintenanceStatus.SCHEDULED.value:
        if new_status != MaintenanceStatus.RESOLVED.value:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"Invalid status transition from {current_status} to {new_status}. "
                    "A scheduled request can only move to RESOLVED."
                )
            )

    elif current_status == MaintenanceStatus.RESOLVED.value:
        if new_status != MaintenanceStatus.TRIAGED.value:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"Invalid status transition from {current_status} to {new_status}. "
                    "A resolved request can only be reopened to TRIAGED (not REPORTED or SCHEDULED)."
                )
            )

    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown status '{current_status}'."
        )

    # Perform transition
    request.status = new_status
    request.updated_at = datetime.now(timezone.utc)

    # Log immutable timeline event
    log_timeline_event(
        db=db,
        request_id=request.id,
        event_type=TimelineEventType.STATUS_CHANGED,
        actor_id=actor.id,
        old_value=current_status,
        new_value=new_status,
        note=status_data.note
    )

    db.commit()
    db.refresh(request)
    return request


def assign_contractors_to_request(
    db: Session,
    request_id: int,
    contractor_ids: List[int],
    actor: User
) -> MaintenanceRequest:
    """
    Assign/unassign contractors to a request.
    Only property managers can call this.
    Logs immutable CONTRACTOR_ASSIGNED and CONTRACTOR_UNASSIGNED timeline events.
    """
    request = get_request_by_id(db, request_id, actor)

    # Verify that all contractor_ids exist and have the contractor role
    contractors = db.query(User).filter(
        User.id.in_(contractor_ids),
        User.role == UserRole.MAINTENANCE_CONTRACTOR.value
    ).all()

    if len(contractors) != len(contractor_ids):
        found_ids = {c.id for c in contractors}
        missing = set(contractor_ids) - found_ids
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"One or more contractor IDs are invalid or not contractors: {list(missing)}"
        )

    current_contractors = list(request.assigned_contractors)
    current_ids = {c.id for c in current_contractors}
    new_ids = set(contractor_ids)

    # Contractors added
    added = [c for c in contractors if c.id not in current_ids]
    # Contractors removed
    removed = [c for c in current_contractors if c.id not in new_ids]

    request.assigned_contractors = contractors
    request.updated_at = datetime.now(timezone.utc)

    for c in added:
        log_timeline_event(
            db=db,
            request_id=request.id,
            event_type=TimelineEventType.CONTRACTOR_ASSIGNED,
            actor_id=actor.id,
            new_value=c.full_name,
            note=f"Assigned contractor: {c.full_name} ({c.email})"
        )

    for c in removed:
        log_timeline_event(
            db=db,
            request_id=request.id,
            event_type=TimelineEventType.CONTRACTOR_UNASSIGNED,
            actor_id=actor.id,
            old_value=c.full_name,
            note=f"Unassigned contractor: {c.full_name} ({c.email})"
        )

    db.commit()
    db.refresh(request)
    return request


def add_note_to_request(
    db: Session,
    request_id: int,
    note_text: str,
    actor: User
) -> MaintenanceTimelineEvent:
    """Add a permanent note to the request timeline."""
    request = get_request_by_id(db, request_id, actor)

    event = log_timeline_event(
        db=db,
        request_id=request.id,
        event_type=TimelineEventType.NOTE_ADDED,
        actor_id=actor.id,
        note=note_text.strip()
    )
    db.commit()
    db.refresh(event)
    return event


def get_requests_filtered(
    db: Session,
    viewer: User,
    query: Optional[str] = None,
    unit_id: Optional[int] = None,
    status_filter: Optional[str] = None,
    priority_filter: Optional[str] = None,
    contractor_id: Optional[int] = None,
    sort_by: str = "created_at",
    sort_order: str = "desc",
    page: int = 1,
    page_size: int = 20
) -> Tuple[List[MaintenanceRequest], int]:
    """
    Search, filter, sort, and paginate maintenance requests completely on the server.
    Enforces contractor visibility boundaries: contractors can only see requests assigned to them!
    """
    q = db.query(MaintenanceRequest).join(Unit, MaintenanceRequest.unit_id == Unit.id)

    # Contractor isolation: must only see requests assigned to them
    if viewer.role == UserRole.MAINTENANCE_CONTRACTOR.value:
        q = q.filter(MaintenanceRequest.assigned_contractors.any(User.id == viewer.id))
    elif contractor_id:
        q = q.filter(MaintenanceRequest.assigned_contractors.any(User.id == contractor_id))

    # Unit filter
    if unit_id:
        q = q.filter(MaintenanceRequest.unit_id == unit_id)

    # Status filter
    if status_filter:
        q = q.filter(MaintenanceRequest.status == status_filter)

    # Priority filter
    if priority_filter:
        q = q.filter(MaintenanceRequest.priority == priority_filter)

    # Text search (description or unit number)
    if query and query.strip():
        term = f"%{query.strip().lower()}%"
        q = q.filter(
            or_(
                func.lower(MaintenanceRequest.description).like(term),
                func.lower(Unit.unit_number).like(term),
                func.lower(Unit.address).like(term)
            )
        )

    # Sorting
    sort_col = MaintenanceRequest.created_at
    if sort_by == "priority":
        sort_col = MaintenanceRequest.priority
    elif sort_by == "status":
        sort_col = MaintenanceRequest.status

    if sort_order.lower() == "asc":
        q = q.order_by(asc(sort_col))
    else:
        q = q.order_by(desc(sort_col))

    total = q.count()
    items = q.offset((page - 1) * page_size).limit(page_size).all()
    return items, total


def to_response_dto(request: MaintenanceRequest) -> MaintenanceRequestResponse:
    """Format a MaintenanceRequest ORM object into a Pydantic DTO with creator & timeline."""
    assigned_contractors = [
        ContractorSummary(id=c.id, full_name=c.full_name, email=c.email)
        for c in request.assigned_contractors
    ]

    events = [
        TimelineEventResponse(
            id=e.id,
            maintenance_request_id=e.maintenance_request_id,
            actor_id=e.actor_id,
            actor_name=e.actor.full_name if e.actor else "System",
            actor_role=e.actor.role if e.actor else None,
            event_type=e.event_type,
            old_value=e.old_value,
            new_value=e.new_value,
            note=e.note,
            created_at=e.created_at
        )
        for e in request.timeline_events
    ]

    return MaintenanceRequestResponse(
        id=request.id,
        unit_id=request.unit_id,
        unit_number=request.unit.unit_number if request.unit else "Unknown",
        unit_address=request.unit.address if request.unit else "Unknown",
        description=request.description,
        priority=MaintenancePriority(request.priority),
        status=MaintenanceStatus(request.status),
        created_by_id=request.created_by_id,
        creator_name=request.creator.full_name if request.creator else "Unknown",
        assigned_contractors=assigned_contractors,
        timeline_events=events,
        created_at=request.created_at,
        updated_at=request.updated_at
    )

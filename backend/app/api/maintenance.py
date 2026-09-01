import math
from typing import List, Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session
from backend.app.db.database import get_db
from backend.app.dependencies.permissions import (
    require_manager,
    require_authenticated,
)
from backend.app.models.user import User, UserRole
from backend.app.schemas.maintenance import (
    MaintenanceRequestCreate,
    MaintenanceRequestUpdate,
    MaintenanceStatusUpdate,
    ContractorAssignRequest,
    AddNoteRequest,
    MaintenanceRequestResponse,
    PaginatedMaintenanceResponse,
    TimelineEventResponse,
)
from backend.app.services.maintenance_service import (
    create_maintenance_request,
    get_request_by_id,
    update_request_details,
    update_request_status,
    assign_contractors_to_request,
    add_note_to_request,
    get_requests_filtered,
    to_response_dto,
)

router = APIRouter(prefix="/maintenance", tags=["Maintenance Requests"])


@router.get("", response_model=PaginatedMaintenanceResponse)
def list_maintenance_requests(
    query: Optional[str] = Query(None, description="Text search on description and unit"),
    unit_id: Optional[int] = Query(None, description="Filter by unit ID"),
    status: Optional[str] = Query(None, description="Filter by status"),
    priority: Optional[str] = Query(None, description="Filter by priority"),
    contractor_id: Optional[int] = Query(None, description="Filter by contractor ID"),
    sort_by: str = Query("created_at", description="Sort by: created_at, priority, status"),
    sort_order: str = Query("desc", description="Sort order: asc, desc"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_authenticated),
):
    """
    Search, filter, sort, and paginate maintenance requests across units.
    Fully executed on the server.
    Contractors strictly see only requests assigned to them.
    """
    items, total = get_requests_filtered(
        db=db,
        viewer=current_user,
        query=query,
        unit_id=unit_id,
        status_filter=status,
        priority_filter=priority,
        contractor_id=contractor_id,
        sort_by=sort_by,
        sort_order=sort_order,
        page=page,
        page_size=page_size
    )

    total_pages = math.ceil(total / page_size) if total > 0 else 1

    return PaginatedMaintenanceResponse(
        items=[to_response_dto(r) for r in items],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages
    )


@router.get("/{request_id}", response_model=MaintenanceRequestResponse)
def get_maintenance_request(
    request_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_authenticated),
):
    """Retrieve full details and timeline of a single maintenance request."""
    request = get_request_by_id(db, request_id, current_user)
    return to_response_dto(request)


@router.post("", response_model=MaintenanceRequestResponse, status_code=status.HTTP_201_CREATED)
def create_request(
    data: MaintenanceRequestCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_authenticated),
):
    """
    Create a new maintenance request in REPORTED status.
    Can be called by either Property Managers or Maintenance Contractors.
    """
    request = create_maintenance_request(db, data, current_user)
    return to_response_dto(request)


@router.patch("/{request_id}", response_model=MaintenanceRequestResponse)
def update_details(
    request_id: int,
    data: MaintenanceRequestUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_authenticated),
):
    """
    Edit description and priority of a request.
    Does NOT modify assigned contractors.
    Can be performed by Property Managers or assigned Contractors.
    """
    request = update_request_details(db, request_id, data, current_user)
    return to_response_dto(request)


@router.patch("/{request_id}/status", response_model=MaintenanceRequestResponse)
def update_status(
    request_id: int,
    status_data: MaintenanceStatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_authenticated),
):
    """
    Transition maintenance request status according to strict lifecycle rules:
    - REPORTED -> TRIAGED
    - TRIAGED -> SCHEDULED (Requires >= 1 assigned contractor; server rejects otherwise)
    - SCHEDULED -> RESOLVED
    - RESOLVED -> TRIAGED (Reopening)
    All other transitions are rejected with clear explanation.
    """
    request = update_request_status(db, request_id, status_data, current_user)
    return to_response_dto(request)


@router.post("/{request_id}/contractors", response_model=MaintenanceRequestResponse)
def assign_contractors(
    request_id: int,
    assign_data: ContractorAssignRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_manager),
):
    """
    Assign/unassign contractors to a maintenance request.
    Restricted to Property Managers.
    Contractors cannot modify assignments.
    """
    request = assign_contractors_to_request(db, request_id, assign_data.contractor_ids, current_user)
    return to_response_dto(request)


@router.post("/{request_id}/notes", response_model=TimelineEventResponse)
def add_note(
    request_id: int,
    note_data: AddNoteRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_authenticated),
):
    """
    Add an immutable note to the request timeline.
    Timeline notes can never be edited or deleted.
    """
    event = add_note_to_request(db, request_id, note_data.note, current_user)
    return TimelineEventResponse(
        id=event.id,
        maintenance_request_id=event.maintenance_request_id,
        actor_id=event.actor_id,
        actor_name=current_user.full_name,
        actor_role=current_user.role,
        event_type=event.event_type,
        old_value=event.old_value,
        new_value=event.new_value,
        note=event.note,
        created_at=event.created_at
    )

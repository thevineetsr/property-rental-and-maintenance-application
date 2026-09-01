from decimal import Decimal
from typing import List, Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session
from backend.app.db.database import get_db
from backend.app.dependencies.permissions import (
    require_manager,
    require_authenticated,
)
from backend.app.models.user import User, UserRole
from backend.app.models.maintenance import MaintenanceStatus
from backend.app.schemas.unit import UnitCreate, UnitUpdate, UnitResponse
from backend.app.schemas.maintenance import MaintenanceRequestResponse
from backend.app.services.unit_service import (
    get_units,
    get_unit_by_id,
    create_unit,
    update_unit,
    archive_unit,
    restore_unit,
)
from backend.app.services.rent_service import (
    get_current_month_str,
    get_unit_month_status,
    get_unit_payments,
)
from backend.app.services.maintenance_service import to_response_dto

router = APIRouter(prefix="/units", tags=["Units"])


@router.get("", response_model=List[UnitResponse])
def list_units(
    include_archived: bool = Query(False, description="Include archived units"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_authenticated),
):
    """
    List units in the portfolio.
    Property managers see full details including rent.
    Contractors have rent data hidden (masked) to strictly enforce server-side privacy.
    """
    units = get_units(db, include_archived=include_archived)
    current_month = get_current_month_str()

    response: List[UnitResponse] = []
    is_contractor = current_user.role == UserRole.MAINTENANCE_CONTRACTOR.value

    for u in units:
        open_count = sum(
            1 for r in u.maintenance_requests
            if r.status != MaintenanceStatus.RESOLVED.value
        )
        rent_status = "N/A"
        monthly_rent = u.monthly_rent

        if is_contractor:
            # Contractors are forbidden from seeing rent amounts or rent status
            monthly_rent = None
            rent_status = "HIDDEN"
        else:
            status_obj = get_unit_month_status(db, u, current_month)
            rent_status = status_obj.status

        dto = UnitResponse(
            id=u.id,
            unit_number=u.unit_number,
            address=u.address,
            monthly_rent=monthly_rent,
            tenant_name=u.tenant_name,
            archived=u.archived,
            created_at=u.created_at,
            updated_at=u.updated_at,
            open_requests_count=open_count,
            current_month_rent_status=rent_status,
        )
        response.append(dto)

    return response


@router.get("/{unit_id}", response_model=UnitResponse)
def get_unit(
    unit_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_authenticated),
):
    """Retrieve details for a single unit."""
    unit = get_unit_by_id(db, unit_id)
    is_contractor = current_user.role == UserRole.MAINTENANCE_CONTRACTOR.value

    monthly_rent = None if is_contractor else unit.monthly_rent
    rent_status = "HIDDEN" if is_contractor else get_unit_month_status(db, unit, get_current_month_str()).status

    open_count = sum(
        1 for r in unit.maintenance_requests
        if r.status != MaintenanceStatus.RESOLVED.value
    )

    return UnitResponse(
        id=unit.id,
        unit_number=unit.unit_number,
        address=unit.address,
        monthly_rent=monthly_rent,
        tenant_name=unit.tenant_name,
        archived=unit.archived,
        created_at=unit.created_at,
        updated_at=unit.updated_at,
        open_requests_count=open_count,
        current_month_rent_status=rent_status,
    )


@router.post("", response_model=UnitResponse, status_code=status.HTTP_201_CREATED)
def create_new_unit(
    unit_data: UnitCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_manager),
):
    """Create a new unit. Restricted to Property Managers."""
    unit = create_unit(db, unit_data)
    return UnitResponse.model_validate(unit)


@router.patch("/{unit_id}", response_model=UnitResponse)
def update_existing_unit(
    unit_id: int,
    unit_data: UnitUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_manager),
):
    """Update unit details. Restricted to Property Managers."""
    unit = update_unit(db, unit_id, unit_data)
    return UnitResponse.model_validate(unit)


@router.post("/{unit_id}/archive", response_model=UnitResponse)
def archive_existing_unit(
    unit_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_manager),
):
    """Soft-delete/archive a unit. Preserves historical records. Restricted to Property Managers."""
    unit = archive_unit(db, unit_id)
    return UnitResponse.model_validate(unit)


@router.post("/{unit_id}/restore", response_model=UnitResponse)
def restore_archived_unit(
    unit_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_manager),
):
    """Restore an archived unit to active portfolio. Restricted to Property Managers."""
    unit = restore_unit(db, unit_id)
    return UnitResponse.model_validate(unit)


@router.get("/{unit_id}/maintenance", response_model=List[MaintenanceRequestResponse])
def get_unit_maintenance_requests(
    unit_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_authenticated),
):
    """Get all maintenance requests belonging to a specific unit."""
    unit = get_unit_by_id(db, unit_id)
    requests = unit.maintenance_requests

    # If contractor, filter only to requests assigned to them
    if current_user.role == UserRole.MAINTENANCE_CONTRACTOR.value:
        requests = [
            r for r in requests
            if any(c.id == current_user.id for c in r.assigned_contractors)
        ]

    return [to_response_dto(r) for r in requests]

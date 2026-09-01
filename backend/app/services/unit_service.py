from typing import List, Optional
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from backend.app.models.unit import Unit
from backend.app.models.maintenance import MaintenanceRequest, MaintenanceStatus
from backend.app.schemas.unit import UnitCreate, UnitUpdate, UnitResponse


def get_units(db: Session, include_archived: bool = False) -> List[Unit]:
    """Retrieve units. By default excludes archived units."""
    query = db.query(Unit)
    if not include_archived:
        query = query.filter(Unit.archived == False)
    return query.order_by(Unit.unit_number.asc()).all()


def get_unit_by_id(db: Session, unit_id: int) -> Unit:
    """Retrieve a single unit by ID or raise 404."""
    unit = db.query(Unit).filter(Unit.id == unit_id).first()
    if not unit:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Unit with ID {unit_id} not found."
        )
    return unit


def create_unit(db: Session, unit_data: UnitCreate) -> Unit:
    """Create a new unit."""
    # Check if active unit with this number already exists
    existing = db.query(Unit).filter(
        Unit.unit_number == unit_data.unit_number.strip(),
        Unit.archived == False
    ).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"An active unit with number '{unit_data.unit_number.strip()}' already exists."
        )
    
    unit = Unit(
        unit_number=unit_data.unit_number.strip(),
        address=unit_data.address.strip(),
        monthly_rent=unit_data.monthly_rent,
        tenant_name=unit_data.tenant_name.strip() if unit_data.tenant_name else None,
        archived=False
    )
    db.add(unit)
    db.commit()
    db.refresh(unit)
    return unit


def update_unit(db: Session, unit_id: int, unit_data: UnitUpdate) -> Unit:
    """Update an existing unit's properties."""
    unit = get_unit_by_id(db, unit_id)
    
    if unit_data.unit_number is not None:
        new_number = unit_data.unit_number.strip()
        # Verify unique among active units
        conflict = db.query(Unit).filter(
            Unit.unit_number == new_number,
            Unit.archived == False,
            Unit.id != unit_id
        ).first()
        if conflict:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"An active unit with number '{new_number}' already exists."
            )
        unit.unit_number = new_number

    if unit_data.address is not None:
        unit.address = unit_data.address.strip()
    if unit_data.monthly_rent is not None:
        unit.monthly_rent = unit_data.monthly_rent
    if unit_data.tenant_name is not None:
        unit.tenant_name = unit_data.tenant_name.strip() if unit_data.tenant_name else None
    
    db.commit()
    db.refresh(unit)
    return unit


def archive_unit(db: Session, unit_id: int) -> Unit:
    """Archive a unit (soft-delete). Preserves all historical records."""
    unit = get_unit_by_id(db, unit_id)
    if unit.archived:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unit is already archived."
        )
    unit.archived = True
    db.commit()
    db.refresh(unit)
    return unit


def restore_unit(db: Session, unit_id: int) -> Unit:
    """Restore an archived unit to the active portfolio view."""
    unit = get_unit_by_id(db, unit_id)
    if not unit.archived:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unit is not archived."
        )
    
    # Check if another active unit has the same unit_number
    conflict = db.query(Unit).filter(
        Unit.unit_number == unit.unit_number,
        Unit.archived == False
    ).first()
    if conflict:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot restore unit: Another active unit with number '{unit.unit_number}' exists."
        )

    unit.archived = False
    db.commit()
    db.refresh(unit)
    return unit

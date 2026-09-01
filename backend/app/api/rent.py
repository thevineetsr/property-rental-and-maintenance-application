from typing import List, Optional
from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session
from backend.app.db.database import get_db
from backend.app.dependencies.permissions import require_manager
from backend.app.models.user import User
from backend.app.schemas.rent import (
    RentPaymentCreate,
    RentPaymentResponse,
    BulkRentRequest,
    BulkRentResponse,
    UnitRentStatusResponse,
    RentAlertResponse,
    DismissAlertRequest,
)
from backend.app.services.rent_service import (
    get_current_month_str,
    record_payment,
    get_unit_payments,
    get_portfolio_rent_roll,
    process_bulk_rent,
    generate_rent_roll_csv,
    get_active_rent_alerts,
    dismiss_rent_alert,
)

router = APIRouter(prefix="/rent", tags=["Rent & Payments"])


@router.get("/status", response_model=List[UnitRentStatusResponse])
def get_rent_status(
    month: Optional[str] = Query(None, description="Month covered in YYYY-MM format"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_manager),
):
    """Retrieve full portfolio rent roll for a specific month. Restricted to Property Managers."""
    month_str = month or get_current_month_str()
    return get_portfolio_rent_roll(db, month_str)


@router.post("/payments", response_model=RentPaymentResponse, status_code=status.HTTP_201_CREATED)
def add_rent_payment(
    payment_data: RentPaymentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_manager),
):
    """Record an individual rent payment for a unit. Restricted to Property Managers."""
    payment = record_payment(db, payment_data)
    return RentPaymentResponse.model_validate(payment)


@router.get("/payments/unit/{unit_id}", response_model=List[RentPaymentResponse])
def list_unit_payments(
    unit_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_manager),
):
    """Get payment history for a specific unit. Restricted to Property Managers."""
    payments = get_unit_payments(db, unit_id)
    return [RentPaymentResponse.model_validate(p) for p in payments]


@router.post("/bulk", response_model=BulkRentResponse)
def bulk_record_rent(
    bulk_data: BulkRentRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_manager),
):
    """
    Bulk-record rent payments received for a given month.
    Returns a per-unit report classifying each row as matched, underpaid, overpaid, or unmatched.
    Restricted to Property Managers.
    """
    return process_bulk_rent(db, bulk_data)


@router.get("/roll/csv")
def download_rent_roll_csv(
    month: Optional[str] = Query(None, description="Month covered in YYYY-MM format"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_manager),
):
    """
    Export the current rent roll as a CSV file.
    Restricted to Property Managers.
    """
    month_str = month or get_current_month_str()
    csv_content = generate_rent_roll_csv(db, month_str)
    
    filename = f"rent_roll_{month_str}.csv"
    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )


@router.get("/alerts", response_model=List[RentAlertResponse])
def get_rent_alerts(
    month: Optional[str] = Query(None, description="Month covered in YYYY-MM format"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_manager),
):
    """
    Retrieve active overdue rent alerts for units whose rent has not been matched
    after the grace period. Restricted to Property Managers.
    """
    month_str = month or get_current_month_str()
    return get_active_rent_alerts(db, month_str)


@router.post("/alerts/{unit_id}/dismiss", status_code=status.HTTP_200_OK)
def dismiss_alert(
    unit_id: int,
    request: DismissAlertRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_manager),
):
    """
    Dismiss a rent alert for a specific unit and month.
    If the unit is unpaid in a subsequent month, the alert will return.
    Restricted to Property Managers.
    """
    dismiss_rent_alert(db, unit_id, request.month_covered, current_user.id)
    return {"message": f"Alert dismissed for unit #{unit_id} for month {request.month_covered}."}

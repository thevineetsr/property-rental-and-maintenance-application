import csv
import io
from datetime import datetime, date, timezone
from decimal import Decimal
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func
from fastapi import HTTPException, status
from backend.app.core.config import settings
from backend.app.models.unit import Unit
from backend.app.models.rent_payment import RentPayment
from backend.app.models.alert import DismissedRentAlert
from backend.app.schemas.rent import (
    RentPaymentCreate,
    BulkRentRequest,
    BulkRentResponse,
    BulkRentRowResult,
    UnitRentStatusResponse,
    RentAlertResponse,
)


def get_current_month_str() -> str:
    """Returns current month formatted as YYYY-MM."""
    return datetime.now(timezone.utc).strftime("%Y-%m")


def calculate_rent_status(
    monthly_rent: Decimal,
    total_paid: Decimal,
    month_covered: str,
    as_of_date: Optional[date] = None
) -> Dict[str, Any]:
    """
    Calculate payment status and overdue state for a unit in a given month.
    
    Rent is due on the 1st of the month.
    Grace period is settings.GRACE_PERIOD_DAYS (e.g. 5 days).
    Rent is overdue only after the grace period expires.
    """
    if as_of_date is None:
        as_of_date = datetime.now(timezone.utc).date()

    try:
        parts = month_covered.split("-")
        cov_year = int(parts[0])
        cov_month = int(parts[1])
    except Exception:
        cov_year = as_of_date.year
        cov_month = as_of_date.month

    # Grace period cut-off date: e.g. 5th of that month
    grace_cutoff_date = date(cov_year, cov_month, min(settings.GRACE_PERIOD_DAYS, 28))

    balance = monthly_rent - total_paid
    is_past_grace = as_of_date > grace_cutoff_date

    if total_paid >= monthly_rent:
        if total_paid == monthly_rent:
            status_str = "PAID"
        else:
            status_str = "OVERPAID"
    elif is_past_grace:
        status_str = "OVERDUE"
    elif total_paid > 0:
        status_str = "UNDERPAID"
    else:
        status_str = "UNPAID"

    return {
        "status": status_str,
        "balance": balance,
        "is_past_grace": is_past_grace,
        "is_overdue": status_str == "OVERDUE"
    }


def record_payment(db: Session, payment_data: RentPaymentCreate) -> RentPayment:
    """Record a rent payment for a unit covering a specific month."""
    unit = db.query(Unit).filter(Unit.id == payment_data.unit_id).first()
    if not unit:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Unit with ID {payment_data.unit_id} does not exist."
        )

    payment = RentPayment(
        unit_id=payment_data.unit_id,
        amount=payment_data.amount,
        month_covered=payment_data.month_covered,
        payment_date=payment_data.payment_date or datetime.now(timezone.utc),
        notes=payment_data.notes
    )
    db.add(payment)
    db.commit()
    db.refresh(payment)
    return payment


def get_unit_payments(db: Session, unit_id: int) -> List[RentPayment]:
    """Retrieve all rent payments for a specific unit, newest first."""
    return db.query(RentPayment).filter(
        RentPayment.unit_id == unit_id
    ).order_by(RentPayment.payment_date.desc()).all()


def get_unit_month_status(db: Session, unit: Unit, month_covered: str) -> UnitRentStatusResponse:
    """Get the calculated rent status for a unit for a specific month."""
    payments = db.query(RentPayment).filter(
        RentPayment.unit_id == unit.id,
        RentPayment.month_covered == month_covered
    ).all()
    total_paid = sum((p.amount for p in payments), Decimal("0.00"))

    calc = calculate_rent_status(unit.monthly_rent, total_paid, month_covered)

    # Check if dismissed
    dismissed = db.query(DismissedRentAlert).filter(
        DismissedRentAlert.unit_id == unit.id,
        DismissedRentAlert.month_covered == month_covered
    ).first()

    is_alert_active = calc["is_overdue"] and (dismissed is None)

    return UnitRentStatusResponse(
        unit_id=unit.id,
        unit_number=unit.unit_number,
        address=unit.address,
        tenant_name=unit.tenant_name,
        monthly_rent=unit.monthly_rent,
        month_covered=month_covered,
        amount_paid=total_paid,
        balance=calc["balance"],
        status=calc["status"],
        is_alert_active=is_alert_active
    )


def get_portfolio_rent_roll(db: Session, month_covered: str) -> List[UnitRentStatusResponse]:
    """Get the full rent roll for all active units for a given month."""
    units = db.query(Unit).filter(Unit.archived == False).order_by(Unit.unit_number.asc()).all()
    return [get_unit_month_status(db, unit, month_covered) for unit in units]


def process_bulk_rent(db: Session, bulk_data: BulkRentRequest) -> BulkRentResponse:
    """
    Process a batch of rent payments for a given month.
    
    Classifies each row into:
    - matched: amount received equals that unit's monthly rent
    - underpaid: amount received falls short of monthly rent
    - overpaid: amount received exceeds monthly rent
    - unmatched: unit identifier does not correspond to any unit
    """
    # Fetch all active units for lookup (by unit_number or ID)
    units = db.query(Unit).filter(Unit.archived == False).all()
    unit_by_num = {u.unit_number.lower(): u for u in units}
    unit_by_id = {str(u.id): u for u in units}

    results: List[BulkRentRowResult] = []
    matched_count = 0
    underpaid_count = 0
    overpaid_count = 0
    unmatched_count = 0

    now_utc = datetime.now(timezone.utc)

    for item in bulk_data.payments:
        key = item.unit_identifier.strip().lower()
        unit = unit_by_num.get(key) or unit_by_id.get(key)

        if not unit:
            unmatched_count += 1
            results.append(
                BulkRentRowResult(
                    unit_identifier=item.unit_identifier,
                    unit_id=None,
                    unit_number=None,
                    tenant_name=None,
                    monthly_rent=None,
                    amount_received=item.amount,
                    classification="unmatched",
                    notes=f"No active unit matches identifier '{item.unit_identifier}'."
                )
            )
            continue

        monthly_rent = unit.monthly_rent
        amount = item.amount

        if amount == monthly_rent:
            classification = "matched"
            matched_count += 1
            notes = "Full monthly rent received."
        elif amount < monthly_rent:
            classification = "underpaid"
            underpaid_count += 1
            notes = f"Underpaid by {monthly_rent - amount}."
        else:
            classification = "overpaid"
            overpaid_count += 1
            notes = f"Overpaid by {amount - monthly_rent}."

        # Record payment in database
        payment = RentPayment(
            unit_id=unit.id,
            amount=amount,
            month_covered=bulk_data.month_covered,
            payment_date=now_utc,
            notes=f"Bulk payment recorded ({classification})"
        )
        db.add(payment)

        results.append(
            BulkRentRowResult(
                unit_identifier=item.unit_identifier,
                unit_id=unit.id,
                unit_number=unit.unit_number,
                tenant_name=unit.tenant_name,
                monthly_rent=monthly_rent,
                amount_received=amount,
                classification=classification,
                notes=notes
            )
        )

    db.commit()

    return BulkRentResponse(
        month_covered=bulk_data.month_covered,
        total_rows=len(bulk_data.payments),
        matched_count=matched_count,
        underpaid_count=underpaid_count,
        overpaid_count=overpaid_count,
        unmatched_count=unmatched_count,
        results=results
    )


def generate_rent_roll_csv(db: Session, month_covered: str) -> str:
    """Generate a CSV string of the rent roll for a given month."""
    roll = get_portfolio_rent_roll(db, month_covered)
    output = io.StringIO()
    writer = csv.writer(output)

    # Header
    writer.writerow([
        "Unit Number",
        "Address",
        "Tenant Name",
        "Monthly Rent",
        "Month Covered",
        "Amount Paid",
        "Remaining Balance",
        "Payment Status"
    ])

    for row in roll:
        writer.writerow([
            row.unit_number,
            row.address,
            row.tenant_name or "Vacant",
            f"{row.monthly_rent:.2f}",
            row.month_covered,
            f"{row.amount_paid:.2f}",
            f"{row.balance:.2f}",
            row.status
        ])

    return output.getvalue()


def get_active_rent_alerts(db: Session, month_covered: str) -> List[RentAlertResponse]:
    """
    Find all active units whose rent has not been matched by a full payment
    once the grace period passes, excluding dismissed alerts for that month.
    """
    roll = get_portfolio_rent_roll(db, month_covered)
    alerts: List[RentAlertResponse] = []

    today = datetime.now(timezone.utc).date()
    try:
        parts = month_covered.split("-")
        cov_year, cov_month = int(parts[0]), int(parts[1])
        grace_cutoff = date(cov_year, cov_month, min(settings.GRACE_PERIOD_DAYS, 28))
    except Exception:
        grace_cutoff = today

    days_overdue = max(0, (today - grace_cutoff).days)

    for item in roll:
        if item.is_alert_active:
            alerts.append(
                RentAlertResponse(
                    unit_id=item.unit_id,
                    unit_number=item.unit_number,
                    tenant_name=item.tenant_name,
                    monthly_rent=item.monthly_rent,
                    month_covered=month_covered,
                    amount_paid=item.amount_paid,
                    balance=item.balance,
                    days_overdue=days_overdue
                )
            )

    return alerts


def dismiss_rent_alert(db: Session, unit_id: int, month_covered: str, user_id: int) -> DismissedRentAlert:
    """Dismiss a rent alert for a specific unit and month."""
    existing = db.query(DismissedRentAlert).filter(
        DismissedRentAlert.unit_id == unit_id,
        DismissedRentAlert.month_covered == month_covered
    ).first()

    if existing:
        return existing

    dismissed = DismissedRentAlert(
        unit_id=unit_id,
        month_covered=month_covered,
        dismissed_by_id=user_id
    )
    db.add(dismissed)
    db.commit()
    db.refresh(dismissed)
    return dismissed

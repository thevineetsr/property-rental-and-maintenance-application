from datetime import datetime, date, timedelta, timezone
from decimal import Decimal
from typing import List, Dict
from sqlalchemy.orm import Session
from sqlalchemy import func
from backend.app.models.unit import Unit
from backend.app.models.user import User, UserRole
from backend.app.models.rent_payment import RentPayment
from backend.app.models.maintenance import (
    MaintenanceRequest,
    MaintenanceStatus,
    MaintenancePriority,
    maintenance_request_contractors,
)
from backend.app.models.timeline import MaintenanceTimelineEvent, TimelineEventType
from backend.app.services.rent_service import (
    get_current_month_str,
    get_portfolio_rent_roll,
)
from backend.app.schemas.dashboard import (
    ManagerDashboardResponse,
    WeeklyResolvedStat,
    UnattendedRequestItem,
    ContractorDashboardResponse,
)


def get_manager_dashboard(db: Session) -> ManagerDashboardResponse:
    """Compute all headline KPIs, breakdowns, trends, and unattended requests for Property Manager."""
    now_utc = datetime.now(timezone.utc)
    current_month = get_current_month_str()

    # Units statistics
    all_units = db.query(Unit).all()
    active_units = [u for u in all_units if not u.archived]
    archived_units = [u for u in all_units if u.archived]

    total_active_units = len(active_units)
    total_archived_units = len(archived_units)
    occupied_units = sum(1 for u in active_units if u.tenant_name and u.tenant_name.strip())
    vacant_units = total_active_units - occupied_units
    monthly_expected_rent = sum((u.monthly_rent for u in active_units), Decimal("0.00"))

    # Rent roll and collections for current month
    rent_roll = get_portfolio_rent_roll(db, current_month)
    total_rent_collected_this_month = sum((r.amount_paid for r in rent_roll), Decimal("0.00"))
    overdue_units_count = sum(1 for r in rent_roll if r.status == "OVERDUE")

    # Maintenance requests statistics
    all_requests = db.query(MaintenanceRequest).all()
    open_statuses = {
        MaintenanceStatus.REPORTED.value,
        MaintenanceStatus.TRIAGED.value,
        MaintenanceStatus.SCHEDULED.value,
    }
    open_requests = [r for r in all_requests if r.status in open_statuses]
    open_count = len(open_requests)
    high_priority_count = sum(1 for r in open_requests if r.priority == MaintenancePriority.HIGH.value)
    scheduled_count = sum(1 for r in all_requests if r.status == MaintenanceStatus.SCHEDULED.value)
    resolved_count = sum(1 for r in all_requests if r.status == MaintenanceStatus.RESOLVED.value)

    # Resolved this week
    one_week_ago = now_utc - timedelta(days=7)
    resolved_this_week = db.query(MaintenanceTimelineEvent).filter(
        MaintenanceTimelineEvent.event_type == TimelineEventType.STATUS_CHANGED.value,
        MaintenanceTimelineEvent.new_value == MaintenanceStatus.RESOLVED.value,
        MaintenanceTimelineEvent.created_at >= one_week_ago
    ).count()

    # Breakdown by status
    requests_by_status = {
        MaintenanceStatus.REPORTED.value: 0,
        MaintenanceStatus.TRIAGED.value: 0,
        MaintenanceStatus.SCHEDULED.value: 0,
        MaintenanceStatus.RESOLVED.value: 0,
    }
    for r in all_requests:
        if r.status in requests_by_status:
            requests_by_status[r.status] += 1

    # Breakdown by contractor (assigned count of open requests)
    contractors = db.query(User).filter(User.role == UserRole.MAINTENANCE_CONTRACTOR.value).all()
    requests_by_contractor = {}
    for c in contractors:
        c_open_count = sum(
            1 for r in open_requests
            if any(assigned.id == c.id for assigned in r.assigned_contractors)
        )
        requests_by_contractor[c.full_name] = c_open_count

    # Trend: Requests resolved per week over the last 8 weeks
    weekly_resolved: List[WeeklyResolvedStat] = []
    for week_idx in range(7, -1, -1):
        w_start = (now_utc - timedelta(days=(week_idx + 1) * 7)).replace(hour=0, minute=0, second=0, microsecond=0)
        w_end = (now_utc - timedelta(days=week_idx * 7)).replace(hour=23, minute=59, second=59, microsecond=999999)

        count = db.query(MaintenanceTimelineEvent).filter(
            MaintenanceTimelineEvent.event_type == TimelineEventType.STATUS_CHANGED.value,
            MaintenanceTimelineEvent.new_value == MaintenanceStatus.RESOLVED.value,
            MaintenanceTimelineEvent.created_at >= w_start,
            MaintenanceTimelineEvent.created_at <= w_end
        ).count()

        weekly_resolved.append(
            WeeklyResolvedStat(
                week_label=w_start.strftime("Wk %V (%b %d)"),
                week_start=w_start.strftime("%Y-%m-%d"),
                resolved_count=count
            )
        )

    # Unattended requests (REPORTED or TRIAGED for >= 14 days)
    fourteen_days_ago = now_utc - timedelta(days=14)
    unattended_raw = db.query(MaintenanceRequest).filter(
        MaintenanceRequest.status.in_([MaintenanceStatus.REPORTED.value, MaintenanceStatus.TRIAGED.value]),
        MaintenanceRequest.created_at <= fourteen_days_ago
    ).order_by(MaintenanceRequest.created_at.asc()).all()

    unattended_list = [
        UnattendedRequestItem(
            id=r.id,
            unit_number=r.unit.unit_number if r.unit else "Unknown",
            description=r.description,
            status=r.status,
            priority=r.priority,
            created_at=r.created_at.strftime("%Y-%m-%d"),
            days_open=(now_utc - r.created_at.replace(tzinfo=timezone.utc if r.created_at.tzinfo is None else None)).days
        )
        for r in unattended_raw
    ]

    return ManagerDashboardResponse(
        total_active_units=total_active_units,
        total_archived_units=total_archived_units,
        occupied_units=occupied_units,
        vacant_units=vacant_units,
        monthly_expected_rent=monthly_expected_rent,
        total_rent_collected_this_month=total_rent_collected_this_month,
        overdue_units_count=overdue_units_count,
        open_maintenance_requests=open_count,
        high_priority_requests=high_priority_count,
        scheduled_requests=scheduled_count,
        resolved_requests=resolved_count,
        requests_resolved_this_week=resolved_this_week,
        requests_by_status=requests_by_status,
        requests_by_contractor=requests_by_contractor,
        weekly_resolved_last_8_weeks=weekly_resolved,
        unattended_requests=unattended_list
    )


def get_contractor_dashboard(db: Session, contractor_id: int) -> ContractorDashboardResponse:
    """Compute summary KPIs for a specific maintenance contractor."""
    contractor = db.query(User).filter(User.id == contractor_id).first()
    if not contractor:
        return ContractorDashboardResponse(
            assigned_requests_count=0,
            open_requests_count=0,
            resolved_requests_count=0,
            high_priority_count=0,
            requests_by_status={}
        )

    assigned = contractor.assigned_requests
    assigned_count = len(assigned)
    open_count = sum(1 for r in assigned if r.status != MaintenanceStatus.RESOLVED.value)
    resolved_count = sum(1 for r in assigned if r.status == MaintenanceStatus.RESOLVED.value)
    high_priority_count = sum(
        1 for r in assigned
        if r.priority == MaintenancePriority.HIGH.value and r.status != MaintenanceStatus.RESOLVED.value
    )

    by_status = {
        MaintenanceStatus.REPORTED.value: 0,
        MaintenanceStatus.TRIAGED.value: 0,
        MaintenanceStatus.SCHEDULED.value: 0,
        MaintenanceStatus.RESOLVED.value: 0,
    }
    for r in assigned:
        if r.status in by_status:
            by_status[r.status] += 1

    return ContractorDashboardResponse(
        assigned_requests_count=assigned_count,
        open_requests_count=open_count,
        resolved_requests_count=resolved_count,
        high_priority_count=high_priority_count,
        requests_by_status=by_status
    )

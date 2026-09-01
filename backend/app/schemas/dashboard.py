from decimal import Decimal
from typing import Dict, List, Any
from pydantic import BaseModel


class WeeklyResolvedStat(BaseModel):
    week_label: str
    week_start: str
    resolved_count: int


class UnattendedRequestItem(BaseModel):
    id: int
    unit_number: str
    description: str
    status: str
    priority: str
    created_at: str
    days_open: int


class ManagerDashboardResponse(BaseModel):
    # Headline KPIs
    total_active_units: int
    total_archived_units: int
    occupied_units: int
    vacant_units: int
    monthly_expected_rent: Decimal
    total_rent_collected_this_month: Decimal
    overdue_units_count: int
    open_maintenance_requests: int
    high_priority_requests: int
    scheduled_requests: int
    resolved_requests: int
    requests_resolved_this_week: int

    # Breakdowns
    requests_by_status: Dict[str, int]
    requests_by_contractor: Dict[str, int]

    # Trends
    weekly_resolved_last_8_weeks: List[WeeklyResolvedStat]

    # Actionable items
    unattended_requests: List[UnattendedRequestItem]


class ContractorDashboardResponse(BaseModel):
    assigned_requests_count: int
    open_requests_count: int
    resolved_requests_count: int
    high_priority_count: int
    requests_by_status: Dict[str, int]

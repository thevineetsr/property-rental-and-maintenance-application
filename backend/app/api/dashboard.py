from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from backend.app.db.database import get_db
from backend.app.dependencies.permissions import (
    require_manager,
    require_contractor,
)
from backend.app.models.user import User
from backend.app.schemas.dashboard import (
    ManagerDashboardResponse,
    ContractorDashboardResponse,
)
from backend.app.services.dashboard_service import (
    get_manager_dashboard,
    get_contractor_dashboard,
)

router = APIRouter(prefix="/dashboard", tags=["Dashboard & Analytics"])


@router.get("/manager", response_model=ManagerDashboardResponse)
def manager_dashboard(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_manager),
):
    """
    Headline metrics, status/contractor breakdowns, 8-week resolved trend,
    overdue rent stats, and unattended maintenance tickets.
    Restricted to Property Managers.
    """
    return get_manager_dashboard(db)


@router.get("/contractor", response_model=ContractorDashboardResponse)
def contractor_dashboard(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_contractor),
):
    """
    Contractor-specific workload metrics: assigned requests, open requests,
    resolved requests, and priority breakdown.
    Restricted to Maintenance Contractors.
    """
    return get_contractor_dashboard(db, current_user.id)

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict
from backend.app.models.maintenance import MaintenancePriority, MaintenanceStatus
from backend.app.models.timeline import TimelineEventType


class ContractorSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    full_name: str
    email: str


class TimelineEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    maintenance_request_id: int
    actor_id: Optional[int] = None
    actor_name: Optional[str] = None
    actor_role: Optional[str] = None
    event_type: str
    old_value: Optional[str] = None
    new_value: Optional[str] = None
    note: Optional[str] = None
    created_at: datetime


class MaintenanceRequestCreate(BaseModel):
    unit_id: int
    description: str = Field(min_length=3)
    priority: MaintenancePriority = MaintenancePriority.MEDIUM


class MaintenanceRequestUpdate(BaseModel):
    description: Optional[str] = Field(default=None, min_length=3)
    priority: Optional[MaintenancePriority] = None


class MaintenanceStatusUpdate(BaseModel):
    status: MaintenanceStatus
    note: Optional[str] = Field(default=None, max_length=1000)


class ContractorAssignRequest(BaseModel):
    contractor_ids: List[int]


class AddNoteRequest(BaseModel):
    note: str = Field(min_length=1, max_length=2000)


class MaintenanceRequestResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    unit_id: int
    unit_number: str
    unit_address: str
    description: str
    priority: MaintenancePriority
    status: MaintenanceStatus
    created_by_id: int
    creator_name: str
    assigned_contractors: List[ContractorSummary] = []
    timeline_events: List[TimelineEventResponse] = []
    created_at: datetime
    updated_at: datetime


class PaginatedMaintenanceResponse(BaseModel):
    items: List[MaintenanceRequestResponse]
    total: int
    page: int
    page_size: int
    total_pages: int

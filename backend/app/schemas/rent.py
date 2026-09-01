from datetime import datetime
from decimal import Decimal
from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict


class RentPaymentCreate(BaseModel):
    unit_id: int
    amount: Decimal = Field(gt=0, decimal_places=2)
    month_covered: str = Field(pattern=r"^\d{4}-(0[1-9]|1[0-2])$", description="Format YYYY-MM")
    payment_date: Optional[datetime] = None
    notes: Optional[str] = Field(default=None, max_length=255)


class RentPaymentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    unit_id: int
    amount: Decimal
    month_covered: str
    payment_date: datetime
    notes: Optional[str] = None
    created_at: datetime


class BulkRentItem(BaseModel):
    unit_identifier: str = Field(min_length=1)
    amount: Decimal = Field(gt=0, decimal_places=2)


class BulkRentRequest(BaseModel):
    month_covered: str = Field(pattern=r"^\d{4}-(0[1-9]|1[0-2])$", description="Format YYYY-MM")
    payments: List[BulkRentItem]


class BulkRentRowResult(BaseModel):
    unit_identifier: str
    unit_id: Optional[int] = None
    unit_number: Optional[str] = None
    tenant_name: Optional[str] = None
    monthly_rent: Optional[Decimal] = None
    amount_received: Decimal
    classification: str  # "matched", "underpaid", "overpaid", "unmatched"
    notes: str


class BulkRentResponse(BaseModel):
    month_covered: str
    total_rows: int
    matched_count: int
    underpaid_count: int
    overpaid_count: int
    unmatched_count: int
    results: List[BulkRentRowResult]


class UnitRentStatusResponse(BaseModel):
    unit_id: int
    unit_number: str
    address: str
    tenant_name: Optional[str] = None
    monthly_rent: Decimal
    month_covered: str
    amount_paid: Decimal
    balance: Decimal
    status: str  # "PAID", "UNDERPAID", "UNPAID", "OVERPAID", "OVERDUE"
    is_alert_active: bool


class RentAlertResponse(BaseModel):
    unit_id: int
    unit_number: str
    tenant_name: Optional[str] = None
    monthly_rent: Decimal
    month_covered: str
    amount_paid: Decimal
    balance: Decimal
    days_overdue: int


class DismissAlertRequest(BaseModel):
    month_covered: str = Field(pattern=r"^\d{4}-(0[1-9]|1[0-2])$", description="Format YYYY-MM")

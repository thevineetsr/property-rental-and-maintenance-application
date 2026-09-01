from datetime import datetime
from decimal import Decimal
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict


class UnitBase(BaseModel):
    unit_number: str = Field(min_length=1, max_length=50)
    address: str = Field(min_length=1, max_length=255)
    monthly_rent: Decimal = Field(gt=0, decimal_places=2)
    tenant_name: Optional[str] = Field(default=None, max_length=255)


class UnitCreate(UnitBase):
    pass


class UnitUpdate(BaseModel):
    unit_number: Optional[str] = Field(default=None, min_length=1, max_length=50)
    address: Optional[str] = Field(default=None, min_length=1, max_length=255)
    monthly_rent: Optional[Decimal] = Field(default=None, gt=0, decimal_places=2)
    tenant_name: Optional[str] = Field(default=None, max_length=255)


class UnitResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    unit_number: str
    address: str
    monthly_rent: Optional[Decimal] = None
    tenant_name: Optional[str] = None
    archived: bool
    created_at: datetime
    updated_at: datetime
    open_requests_count: Optional[int] = 0
    current_month_rent_status: Optional[str] = None

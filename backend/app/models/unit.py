from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Numeric, Boolean, DateTime
from sqlalchemy.orm import relationship
from backend.app.db.database import Base


class Unit(Base):
    __tablename__ = "units"

    id = Column(Integer, primary_key=True, index=True)
    unit_number = Column(String(50), nullable=False, index=True)
    address = Column(String(255), nullable=False)
    monthly_rent = Column(Numeric(10, 2), nullable=False)
    tenant_name = Column(String(255), nullable=True)  # Nullable if vacant
    archived = Column(Boolean, default=False, nullable=False, index=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    # Relationships
    rent_payments = relationship(
        "RentPayment",
        back_populates="unit",
        cascade="all, delete-orphan",
        order_by="RentPayment.payment_date.desc()"
    )
    maintenance_requests = relationship(
        "MaintenanceRequest",
        back_populates="unit",
        cascade="all, delete-orphan",
        order_by="MaintenanceRequest.created_at.desc()"
    )
    dismissed_alerts = relationship(
        "DismissedRentAlert",
        back_populates="unit",
        cascade="all, delete-orphan"
    )

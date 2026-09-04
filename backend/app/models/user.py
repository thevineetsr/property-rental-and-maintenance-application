import enum
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.orm import relationship
from backend.app.db.database import Base


class UserRole(str, enum.Enum):
    PROPERTY_MANAGER = "PROPERTY_MANAGER"
    MAINTENANCE_CONTRACTOR = "MAINTENANCE_CONTRACTOR"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    test = Column(String(255), unique=False, index=False, nullable=True)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=False)
    role = Column(String(50), nullable=False, default=UserRole.PROPERTY_MANAGER.value)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    # Relationships
    created_requests = relationship(
        "MaintenanceRequest",
        back_populates="creator",
        foreign_keys="MaintenanceRequest.created_by_id"
    )
    assigned_requests = relationship(
        "MaintenanceRequest",
        secondary="maintenance_request_contractors",
        back_populates="assigned_contractors"
    )
    timeline_events = relationship(
        "MaintenanceTimelineEvent",
        back_populates="actor"
    )
    dismissed_alerts = relationship(
        "DismissedRentAlert",
        back_populates="dismissed_by"
    )

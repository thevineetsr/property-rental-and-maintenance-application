import enum
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Table
from sqlalchemy.orm import relationship
from backend.app.db.database import Base


class MaintenancePriority(str, enum.Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class MaintenanceStatus(str, enum.Enum):
    REPORTED = "REPORTED"
    TRIAGED = "TRIAGED"
    SCHEDULED = "SCHEDULED"
    RESOLVED = "RESOLVED"


# Association table for Many-to-Many relationship between MaintenanceRequest and Contractor (User)
maintenance_request_contractors = Table(
    "maintenance_request_contractors",
    Base.metadata,
    Column(
        "maintenance_request_id",
        Integer,
        ForeignKey("maintenance_requests.id", ondelete="CASCADE"),
        primary_key=True
    ),
    Column(
        "contractor_id",
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True
    ),
    Column(
        "assigned_at",
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )
)


class MaintenanceRequest(Base):
    __tablename__ = "maintenance_requests"

    id = Column(Integer, primary_key=True, index=True)
    unit_id = Column(Integer, ForeignKey("units.id", ondelete="CASCADE"), nullable=False, index=True)
    description = Column(Text, nullable=False)
    priority = Column(String(20), nullable=False, default=MaintenancePriority.MEDIUM.value, index=True)
    status = Column(String(20), nullable=False, default=MaintenanceStatus.REPORTED.value, index=True)
    created_by_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False, index=True)
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    # Relationships
    unit = relationship("Unit", back_populates="maintenance_requests")
    creator = relationship("User", foreign_keys=[created_by_id], back_populates="created_requests")
    assigned_contractors = relationship(
        "User",
        secondary=maintenance_request_contractors,
        back_populates="assigned_requests"
    )
    timeline_events = relationship(
        "MaintenanceTimelineEvent",
        back_populates="maintenance_request",
        cascade="all, delete-orphan",
        order_by="MaintenanceTimelineEvent.created_at.asc()"
    )

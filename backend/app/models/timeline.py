import enum
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from backend.app.db.database import Base


class TimelineEventType(str, enum.Enum):
    CREATED = "CREATED"
    STATUS_CHANGED = "STATUS_CHANGED"
    CONTRACTOR_ASSIGNED = "CONTRACTOR_ASSIGNED"
    CONTRACTOR_UNASSIGNED = "CONTRACTOR_UNASSIGNED"
    NOTE_ADDED = "NOTE_ADDED"
    DETAILS_UPDATED = "DETAILS_UPDATED"


class MaintenanceTimelineEvent(Base):
    __tablename__ = "maintenance_timeline_events"

    id = Column(Integer, primary_key=True, index=True)
    maintenance_request_id = Column(
        Integer,
        ForeignKey("maintenance_requests.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    actor_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    event_type = Column(String(50), nullable=False)
    old_value = Column(String(255), nullable=True)
    new_value = Column(String(255), nullable=True)
    note = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    maintenance_request = relationship("MaintenanceRequest", back_populates="timeline_events")
    actor = relationship("User", back_populates="timeline_events")

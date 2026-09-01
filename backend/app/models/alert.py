from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from backend.app.db.database import Base


class DismissedRentAlert(Base):
    __tablename__ = "dismissed_rent_alerts"

    id = Column(Integer, primary_key=True, index=True)
    unit_id = Column(Integer, ForeignKey("units.id", ondelete="CASCADE"), nullable=False, index=True)
    month_covered = Column(String(7), nullable=False, index=True)  # Format: YYYY-MM
    dismissed_by_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    dismissed_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    __table_args__ = (
        UniqueConstraint("unit_id", "month_covered", name="uq_dismissed_alert_unit_month"),
    )

    # Relationships
    unit = relationship("Unit", back_populates="dismissed_alerts")
    dismissed_by = relationship("User", back_populates="dismissed_alerts")

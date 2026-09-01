"""
Database seed script to populate realistic demo data for:
- Property Manager
- Maintenance Contractors
- Active, Occupied, Vacant, and Archived Units
- Rent Payments (Paid, Underpaid, Overdue)
- Maintenance Requests across all statuses (Reported, Triaged, Scheduled, Resolved)
- Immutable Timeline Audit Events and Notes
"""

from datetime import datetime, date, timedelta, timezone
from decimal import Decimal
from backend.app.db.database import SessionLocal
from backend.app.core.security import hash_password
from backend.app.models.user import User, UserRole
from backend.app.models.unit import Unit
from backend.app.models.rent_payment import RentPayment
from backend.app.models.maintenance import (
    MaintenanceRequest,
    MaintenancePriority,
    MaintenanceStatus,
)
from backend.app.models.timeline import MaintenanceTimelineEvent, TimelineEventType
from backend.app.services.rent_service import get_current_month_str


def seed():
    db = SessionLocal()
    try:
        print("[INFO] Seeding database...")
        now = datetime.now(timezone.utc)
        current_month = get_current_month_str()

        # Compute previous month string
        first_day_current = now.replace(day=1)
        last_day_prev = first_day_current - timedelta(days=1)
        prev_month = last_day_prev.strftime("%Y-%m")

        # 1. Create Users
        manager = db.query(User).filter(User.email == "manager@property.com").first()
        if not manager:
            manager = User(
                email="manager@property.com",
                password_hash=hash_password("Manager123!"),
                full_name="Sarah Jenkins (Manager)",
                role=UserRole.PROPERTY_MANAGER.value
            )
            db.add(manager)

        contractor_bob = db.query(User).filter(User.email == "bob@contractor.com").first()
        if not contractor_bob:
            contractor_bob = User(
                email="bob@contractor.com",
                password_hash=hash_password("Contractor123!"),
                full_name="Bob Fixit (Plumbing & HVAC)",
                role=UserRole.MAINTENANCE_CONTRACTOR.value
            )
            db.add(contractor_bob)

        contractor_alice = db.query(User).filter(User.email == "alice@contractor.com").first()
        if not contractor_alice:
            contractor_alice = User(
                email="alice@contractor.com",
                password_hash=hash_password("Contractor123!"),
                full_name="Alice Sparks (Electrical & General)",
                role=UserRole.MAINTENANCE_CONTRACTOR.value
            )
            db.add(contractor_alice)

        db.flush()

        # 2. Create Units
        units_data = [
            {"unit_number": "101", "address": "742 Evergreen Terrace, Apt 101", "monthly_rent": Decimal("1500.00"), "tenant_name": "Homer Simpson", "archived": False},
            {"unit_number": "102", "address": "742 Evergreen Terrace, Apt 102", "monthly_rent": Decimal("1400.00"), "tenant_name": "Ned Flanders", "archived": False},
            {"unit_number": "201", "address": "742 Evergreen Terrace, Apt 201", "monthly_rent": Decimal("1650.00"), "tenant_name": "Seymour Skinner", "archived": False},
            {"unit_number": "202", "address": "742 Evergreen Terrace, Apt 202", "monthly_rent": Decimal("1550.00"), "tenant_name": None, "archived": False},  # Vacant
            {"unit_number": "301", "address": "742 Evergreen Terrace, Apt 301", "monthly_rent": Decimal("1800.00"), "tenant_name": "Edna Krabappel", "archived": False},
            {"unit_number": "302", "address": "742 Evergreen Terrace, Apt 302", "monthly_rent": Decimal("1750.00"), "tenant_name": "Apu Nahasapeemapetilon", "archived": False},
            {"unit_number": "Old-404", "address": "742 Evergreen Terrace, Penthouse", "monthly_rent": Decimal("2500.00"), "tenant_name": "Charles Montgomery Burns", "archived": True},
        ]

        unit_objs = {}
        for u in units_data:
            existing = db.query(Unit).filter(Unit.unit_number == u["unit_number"]).first()
            if not existing:
                unit = Unit(
                    unit_number=u["unit_number"],
                    address=u["address"],
                    monthly_rent=u["monthly_rent"],
                    tenant_name=u["tenant_name"],
                    archived=u["archived"]
                )
                db.add(unit)
                db.flush()
                unit_objs[u["unit_number"]] = unit
            else:
                unit_objs[u["unit_number"]] = existing

        # 3. Create Rent Payments
        # Unit 101: Paid in full for current and previous month
        u101 = unit_objs["101"]
        if not db.query(RentPayment).filter(RentPayment.unit_id == u101.id, RentPayment.month_covered == current_month).first():
            db.add(RentPayment(unit_id=u101.id, amount=Decimal("1500.00"), month_covered=current_month, payment_date=now - timedelta(days=2), notes="Bank transfer - Full payment"))
        if not db.query(RentPayment).filter(RentPayment.unit_id == u101.id, RentPayment.month_covered == prev_month).first():
            db.add(RentPayment(unit_id=u101.id, amount=Decimal("1500.00"), month_covered=prev_month, payment_date=now - timedelta(days=32), notes="Check #401"))

        # Unit 102: Underpaid ($1000 of $1400)
        u102 = unit_objs["102"]
        if not db.query(RentPayment).filter(RentPayment.unit_id == u102.id, RentPayment.month_covered == current_month).first():
            db.add(RentPayment(unit_id=u102.id, amount=Decimal("1000.00"), month_covered=current_month, payment_date=now - timedelta(days=3), notes="Partial payment via direct deposit"))

        # Unit 201: Overdue! 0 payment for current month, paid for prev month
        u201 = unit_objs["201"]
        if not db.query(RentPayment).filter(RentPayment.unit_id == u201.id, RentPayment.month_covered == prev_month).first():
            db.add(RentPayment(unit_id=u201.id, amount=Decimal("1650.00"), month_covered=prev_month, payment_date=now - timedelta(days=33), notes="Bank transfer"))

        # Unit 301: Paid in full
        u301 = unit_objs["301"]
        if not db.query(RentPayment).filter(RentPayment.unit_id == u301.id, RentPayment.month_covered == current_month).first():
            db.add(RentPayment(unit_id=u301.id, amount=Decimal("1800.00"), month_covered=current_month, payment_date=now - timedelta(days=1), notes="Auto-pay"))

        # Unit 302: Paid in full
        u302 = unit_objs["302"]
        if not db.query(RentPayment).filter(RentPayment.unit_id == u302.id, RentPayment.month_covered == current_month).first():
            db.add(RentPayment(unit_id=u302.id, amount=Decimal("1750.00"), month_covered=current_month, payment_date=now - timedelta(days=1), notes="Electronic transfer"))

        # Archived Unit Old-404: historical payments preserved
        u404 = unit_objs["Old-404"]
        if not db.query(RentPayment).filter(RentPayment.unit_id == u404.id).first():
            db.add(RentPayment(unit_id=u404.id, amount=Decimal("2500.00"), month_covered=prev_month, payment_date=now - timedelta(days=40), notes="Historic payment"))

        db.flush()

        # 4. Create Maintenance Requests with Lifecycles and Timelines
        req1 = db.query(MaintenanceRequest).filter(MaintenanceRequest.description == "Leaking kitchen pipe under the sink").first()
        if not req1:
            req1 = MaintenanceRequest(
                unit_id=u101.id,
                description="Leaking kitchen pipe under the sink",
                priority=MaintenancePriority.HIGH.value,
                status=MaintenanceStatus.SCHEDULED.value,
                created_by_id=manager.id,
                created_at=now - timedelta(days=3),
                updated_at=now - timedelta(days=1)
            )
            req1.assigned_contractors.append(contractor_bob)
            db.add(req1)
            db.flush()

            db.add(MaintenanceTimelineEvent(
                maintenance_request_id=req1.id,
                actor_id=manager.id,
                event_type=TimelineEventType.CREATED.value,
                new_value=MaintenanceStatus.REPORTED.value,
                note="Tenant phoned in reporting continuous leak under the sink basin",
                created_at=now - timedelta(days=3)
            ))
            db.add(MaintenanceTimelineEvent(
                maintenance_request_id=req1.id,
                actor_id=manager.id,
                event_type=TimelineEventType.STATUS_CHANGED.value,
                old_value=MaintenanceStatus.REPORTED.value,
                new_value=MaintenanceStatus.TRIAGED.value,
                note="Assessed severity: urgent repair needed to prevent cabinet damage",
                created_at=now - timedelta(days=2, hours=18)
            ))
            db.add(MaintenanceTimelineEvent(
                maintenance_request_id=req1.id,
                actor_id=manager.id,
                event_type=TimelineEventType.CONTRACTOR_ASSIGNED.value,
                new_value=contractor_bob.full_name,
                note=f"Assigned contractor: {contractor_bob.full_name}",
                created_at=now - timedelta(days=2, hours=10)
            ))
            db.add(MaintenanceTimelineEvent(
                maintenance_request_id=req1.id,
                actor_id=manager.id,
                event_type=TimelineEventType.STATUS_CHANGED.value,
                old_value=MaintenanceStatus.TRIAGED.value,
                new_value=MaintenanceStatus.SCHEDULED.value,
                note="Contractor scheduled for on-site visit tomorrow morning at 10 AM",
                created_at=now - timedelta(days=1)
            ))

        # Request 2: TRIAGED, electrical
        req2 = db.query(MaintenanceRequest).filter(MaintenanceRequest.description == "Flickering overhead light in living room").first()
        if not req2:
            req2 = MaintenanceRequest(
                unit_id=u102.id,
                description="Flickering overhead light in living room",
                priority=MaintenancePriority.MEDIUM.value,
                status=MaintenanceStatus.TRIAGED.value,
                created_by_id=contractor_alice.id,
                created_at=now - timedelta(days=4),
                updated_at=now - timedelta(days=3)
            )
            db.add(req2)
            db.flush()

            db.add(MaintenanceTimelineEvent(
                maintenance_request_id=req2.id,
                actor_id=contractor_alice.id,
                event_type=TimelineEventType.CREATED.value,
                new_value=MaintenanceStatus.REPORTED.value,
                note="Noticed during routine fixture inspection",
                created_at=now - timedelta(days=4)
            ))
            db.add(MaintenanceTimelineEvent(
                maintenance_request_id=req2.id,
                actor_id=manager.id,
                event_type=TimelineEventType.STATUS_CHANGED.value,
                old_value=MaintenanceStatus.REPORTED.value,
                new_value=MaintenanceStatus.TRIAGED.value,
                note="Triaged: awaiting contractor availability confirmation",
                created_at=now - timedelta(days=3)
            ))

        # Request 3: RESOLVED, heating
        req3 = db.query(MaintenanceRequest).filter(MaintenanceRequest.description == "Water heater temperature fluctuating").first()
        if not req3:
            req3 = MaintenanceRequest(
                unit_id=u201.id,
                description="Water heater temperature fluctuating",
                priority=MaintenancePriority.HIGH.value,
                status=MaintenanceStatus.RESOLVED.value,
                created_by_id=manager.id,
                created_at=now - timedelta(days=8),
                updated_at=now - timedelta(days=2)
            )
            req3.assigned_contractors.append(contractor_bob)
            db.add(req3)
            db.flush()

            db.add(MaintenanceTimelineEvent(
                maintenance_request_id=req3.id,
                actor_id=manager.id,
                event_type=TimelineEventType.CREATED.value,
                new_value=MaintenanceStatus.REPORTED.value,
                note="Hot water cutting off during showers",
                created_at=now - timedelta(days=8)
            ))
            db.add(MaintenanceTimelineEvent(
                maintenance_request_id=req3.id,
                actor_id=manager.id,
                event_type=TimelineEventType.STATUS_CHANGED.value,
                old_value=MaintenanceStatus.REPORTED.value,
                new_value=MaintenanceStatus.TRIAGED.value,
                created_at=now - timedelta(days=7)
            ))
            db.add(MaintenanceTimelineEvent(
                maintenance_request_id=req3.id,
                actor_id=manager.id,
                event_type=TimelineEventType.CONTRACTOR_ASSIGNED.value,
                new_value=contractor_bob.full_name,
                created_at=now - timedelta(days=6)
            ))
            db.add(MaintenanceTimelineEvent(
                maintenance_request_id=req3.id,
                actor_id=manager.id,
                event_type=TimelineEventType.STATUS_CHANGED.value,
                old_value=MaintenanceStatus.TRIAGED.value,
                new_value=MaintenanceStatus.SCHEDULED.value,
                created_at=now - timedelta(days=5)
            ))
            db.add(MaintenanceTimelineEvent(
                maintenance_request_id=req3.id,
                actor_id=contractor_bob.id,
                event_type=TimelineEventType.STATUS_CHANGED.value,
                old_value=MaintenanceStatus.SCHEDULED.value,
                new_value=MaintenanceStatus.RESOLVED.value,
                note="Replaced heating element and calibrated thermostat. Operating normally.",
                created_at=now - timedelta(days=2)
            ))

        # Request 4: UNATTENDED (>14 days) in REPORTED
        req4 = db.query(MaintenanceRequest).filter(MaintenanceRequest.description == "Front door deadbolt lock sticks when cold").first()
        if not req4:
            req4 = MaintenanceRequest(
                unit_id=u301.id,
                description="Front door deadbolt lock sticks when cold",
                priority=MaintenancePriority.LOW.value,
                status=MaintenanceStatus.REPORTED.value,
                created_by_id=manager.id,
                created_at=now - timedelta(days=16),
                updated_at=now - timedelta(days=16)
            )
            db.add(req4)
            db.flush()

            db.add(MaintenanceTimelineEvent(
                maintenance_request_id=req4.id,
                actor_id=manager.id,
                event_type=TimelineEventType.CREATED.value,
                new_value=MaintenanceStatus.REPORTED.value,
                note="Tenant notified management by email 16 days ago",
                created_at=now - timedelta(days=16)
            ))

        # Request 5: Multiple contractors assigned (M:N) in SCHEDULED
        req5 = db.query(MaintenanceRequest).filter(MaintenanceRequest.description == "HVAC compressor humming and electrical circuit tripping").first()
        if not req5:
            req5 = MaintenanceRequest(
                unit_id=u302.id,
                description="HVAC compressor humming and electrical circuit tripping",
                priority=MaintenancePriority.HIGH.value,
                status=MaintenanceStatus.SCHEDULED.value,
                created_by_id=manager.id,
                created_at=now - timedelta(days=5),
                updated_at=now - timedelta(days=1)
            )
            req5.assigned_contractors.extend([contractor_bob, contractor_alice])
            db.add(req5)
            db.flush()

            db.add(MaintenanceTimelineEvent(
                maintenance_request_id=req5.id,
                actor_id=manager.id,
                event_type=TimelineEventType.CREATED.value,
                new_value=MaintenanceStatus.REPORTED.value,
                note="AC unit causes living room breaker to trip intermittently",
                created_at=now - timedelta(days=5)
            ))
            db.add(MaintenanceTimelineEvent(
                maintenance_request_id=req5.id,
                actor_id=manager.id,
                event_type=TimelineEventType.STATUS_CHANGED.value,
                old_value=MaintenanceStatus.REPORTED.value,
                new_value=MaintenanceStatus.TRIAGED.value,
                created_at=now - timedelta(days=4)
            ))
            db.add(MaintenanceTimelineEvent(
                maintenance_request_id=req5.id,
                actor_id=manager.id,
                event_type=TimelineEventType.CONTRACTOR_ASSIGNED.value,
                new_value=contractor_bob.full_name,
                note="Assigned Bob Fixit for HVAC compressor diagnosis",
                created_at=now - timedelta(days=3)
            ))
            db.add(MaintenanceTimelineEvent(
                maintenance_request_id=req5.id,
                actor_id=manager.id,
                event_type=TimelineEventType.CONTRACTOR_ASSIGNED.value,
                new_value=contractor_alice.full_name,
                note="Assigned Alice Sparks for breaker panel inspection",
                created_at=now - timedelta(days=3)
            ))
            db.add(MaintenanceTimelineEvent(
                maintenance_request_id=req5.id,
                actor_id=manager.id,
                event_type=TimelineEventType.STATUS_CHANGED.value,
                old_value=MaintenanceStatus.TRIAGED.value,
                new_value=MaintenanceStatus.SCHEDULED.value,
                note="Joint inspection scheduled for Friday at 2 PM",
                created_at=now - timedelta(days=1)
            ))

        db.commit()
        print("[SUCCESS] Seeding completed successfully!")
        print("\nDemo Credentials:")
        print("----------------------------------------------------------------")
        print("Property Manager:       manager@property.com  /  Manager123!")
        print("Maintenance Contractor: bob@contractor.com    /  Contractor123!")
        print("Maintenance Contractor: alice@contractor.com  /  Contractor123!")
        print("----------------------------------------------------------------\n")
    except Exception as e:
        db.rollback()
        print(f"[ERROR] Error seeding database: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed()

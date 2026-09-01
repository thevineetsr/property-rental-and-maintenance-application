from decimal import Decimal
from backend.app.models.unit import Unit


def test_bulk_rent_recording(client, manager_token, db, test_unit):
    # Create extra units for test
    unit2 = Unit(unit_number="T-102", address="102 Test St", monthly_rent=Decimal("1000.00"), archived=False)
    unit3 = Unit(unit_number="T-103", address="103 Test St", monthly_rent=Decimal("1500.00"), archived=False)
    db.add_all([unit2, unit3])
    db.commit()

    bulk_payload = {
        "month_covered": "2026-10",
        "payments": [
            {"unit_identifier": test_unit.unit_number, "amount": 1200.00},  # matched (1200 == 1200)
            {"unit_identifier": "T-102", "amount": 800.00},                  # underpaid (800 < 1000)
            {"unit_identifier": "T-103", "amount": 1600.00},                 # overpaid (1600 > 1500)
            {"unit_identifier": "GHOST-UNIT", "amount": 500.00},             # unmatched
        ]
    }

    res = client.post(
        "/api/rent/bulk",
        json=bulk_payload,
        headers={"Authorization": f"Bearer {manager_token}"}
    )
    assert res.status_code == 200
    data = res.json()

    assert data["total_rows"] == 4
    assert data["matched_count"] == 1
    assert data["underpaid_count"] == 1
    assert data["overpaid_count"] == 1
    assert data["unmatched_count"] == 1

    # Check classifications in result rows
    row_classifications = {r["unit_identifier"]: r["classification"] for r in data["results"]}
    assert row_classifications[test_unit.unit_number] == "matched"
    assert row_classifications["T-102"] == "underpaid"
    assert row_classifications["T-103"] == "overpaid"
    assert row_classifications["GHOST-UNIT"] == "unmatched"

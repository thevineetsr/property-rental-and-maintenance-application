def test_maintenance_lifecycle_rules(client, manager_token, test_users, test_unit):
    # 1. Create request -> starts in REPORTED
    create_res = client.post(
        "/api/maintenance",
        json={
            "unit_id": test_unit.id,
            "description": "Bathroom pipe is dripping",
            "priority": "HIGH"
        },
        headers={"Authorization": f"Bearer {manager_token}"}
    )
    assert create_res.status_code == 201
    req = create_res.json()
    req_id = req["id"]
    assert req["status"] == "REPORTED"

    # 2. Try illegal jump REPORTED -> SCHEDULED (must fail)
    res = client.patch(
        f"/api/maintenance/{req_id}/status",
        json={"status": "SCHEDULED"},
        headers={"Authorization": f"Bearer {manager_token}"}
    )
    assert res.status_code == 400
    assert "Invalid status transition" in res.json()["detail"]

    # 3. Valid transition: REPORTED -> TRIAGED
    res = client.patch(
        f"/api/maintenance/{req_id}/status",
        json={"status": "TRIAGED", "note": "Issue assessed"},
        headers={"Authorization": f"Bearer {manager_token}"}
    )
    assert res.status_code == 200
    assert res.json()["status"] == "TRIAGED"

    # 4. Try TRIAGED -> SCHEDULED WITHOUT contractor (MUST FAIL per Requirement 4)
    res = client.patch(
        f"/api/maintenance/{req_id}/status",
        json={"status": "SCHEDULED"},
        headers={"Authorization": f"Bearer {manager_token}"}
    )
    assert res.status_code == 400
    assert "Cannot schedule maintenance request because no contractor is assigned" in res.json()["detail"]

    # 5. Assign contractor (Bob)
    assign_res = client.post(
        f"/api/maintenance/{req_id}/contractors",
        json={"contractor_ids": [test_users["contractor1"].id]},
        headers={"Authorization": f"Bearer {manager_token}"}
    )
    assert assign_res.status_code == 200
    assert len(assign_res.json()["assigned_contractors"]) == 1

    # 6. Now TRIAGED -> SCHEDULED must SUCCEED
    res = client.patch(
        f"/api/maintenance/{req_id}/status",
        json={"status": "SCHEDULED", "note": "Contractor assigned and ready"},
        headers={"Authorization": f"Bearer {manager_token}"}
    )
    assert res.status_code == 200
    assert res.json()["status"] == "SCHEDULED"

    # 7. Try illegal SCHEDULED -> REPORTED (must fail)
    res = client.patch(
        f"/api/maintenance/{req_id}/status",
        json={"status": "REPORTED"},
        headers={"Authorization": f"Bearer {manager_token}"}
    )
    assert res.status_code == 400

    # 8. Valid transition: SCHEDULED -> RESOLVED
    res = client.patch(
        f"/api/maintenance/{req_id}/status",
        json={"status": "RESOLVED", "note": "Pipe replaced and leak sealed"},
        headers={"Authorization": f"Bearer {manager_token}"}
    )
    assert res.status_code == 200
    assert res.json()["status"] == "RESOLVED"

    # 9. Try illegal RESOLVED -> REPORTED (must fail, reopen must return to TRIAGED)
    res = client.patch(
        f"/api/maintenance/{req_id}/status",
        json={"status": "REPORTED"},
        headers={"Authorization": f"Bearer {manager_token}"}
    )
    assert res.status_code == 400
    assert "reopened to TRIAGED" in res.json()["detail"]

    # 10. Valid reopen: RESOLVED -> TRIAGED
    res = client.patch(
        f"/api/maintenance/{req_id}/status",
        json={"status": "TRIAGED", "note": "Tenant reports damp spot still appears"},
        headers={"Authorization": f"Bearer {manager_token}"}
    )
    assert res.status_code == 200
    assert res.json()["status"] == "TRIAGED"

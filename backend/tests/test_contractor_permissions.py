def test_contractor_assignment_forbidden(client, contractor1_token, test_users, test_unit, manager_token):
    # Manager creates request
    create_res = client.post(
        "/api/maintenance",
        json={"unit_id": test_unit.id, "description": "Faulty thermostat", "priority": "MEDIUM"},
        headers={"Authorization": f"Bearer {manager_token}"}
    )
    req_id = create_res.json()["id"]

    # Contractor attempts to assign themselves -> 403 Forbidden
    res = client.post(
        f"/api/maintenance/{req_id}/contractors",
        json={"contractor_ids": [test_users["contractor1"].id]},
        headers={"Authorization": f"Bearer {contractor1_token}"}
    )
    assert res.status_code == 403


def test_contractor_isolation(client, manager_token, contractor1_token, contractor2_token, test_users, test_unit):
    # Create request assigned to Contractor 1 (Bob)
    res = client.post(
        "/api/maintenance",
        json={"unit_id": test_unit.id, "description": "Bob's private assignment", "priority": "LOW"},
        headers={"Authorization": f"Bearer {manager_token}"}
    )
    req_id = res.json()["id"]

    client.post(
        f"/api/maintenance/{req_id}/contractors",
        json={"contractor_ids": [test_users["contractor1"].id]},
        headers={"Authorization": f"Bearer {manager_token}"}
    )

    # Bob (Contractor 1) can view the request
    res = client.get(f"/api/maintenance/{req_id}", headers={"Authorization": f"Bearer {contractor1_token}"})
    assert res.status_code == 200
    assert res.json()["id"] == req_id

    # Alice (Contractor 2) CANNOT view Bob's request -> 403 Forbidden
    res = client.get(f"/api/maintenance/{req_id}", headers={"Authorization": f"Bearer {contractor2_token}"})
    assert res.status_code == 403
    assert "Access denied" in res.json()["detail"]

    # In maintenance list, Alice does not see Bob's request
    res = client.get("/api/maintenance", headers={"Authorization": f"Bearer {contractor2_token}"})
    assert res.status_code == 200
    returned_ids = [r["id"] for r in res.json()["items"]]
    assert req_id not in returned_ids


def test_contractor_can_update_details_and_add_note(client, manager_token, contractor1_token, test_users, test_unit):
    # Create request and assign Bob
    res = client.post(
        "/api/maintenance",
        json={"unit_id": test_unit.id, "description": "Original description", "priority": "LOW"},
        headers={"Authorization": f"Bearer {manager_token}"}
    )
    req_id = res.json()["id"]

    client.post(
        f"/api/maintenance/{req_id}/contractors",
        json={"contractor_ids": [test_users["contractor1"].id]},
        headers={"Authorization": f"Bearer {manager_token}"}
    )

    # Bob edits description & priority
    res = client.patch(
        f"/api/maintenance/{req_id}",
        json={"description": "Updated by contractor", "priority": "HIGH"},
        headers={"Authorization": f"Bearer {contractor1_token}"}
    )
    assert res.status_code == 200
    assert res.json()["description"] == "Updated by contractor"
    assert res.json()["priority"] == "HIGH"

    # Bob adds timeline note
    res = client.post(
        f"/api/maintenance/{req_id}/notes",
        json={"note": "Parts ordered from supplier."},
        headers={"Authorization": f"Bearer {contractor1_token}"}
    )
    assert res.status_code == 200
    assert res.json()["note"] == "Parts ordered from supplier."

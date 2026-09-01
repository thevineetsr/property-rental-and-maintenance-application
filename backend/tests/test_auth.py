def test_register_success(client):
    res = client.post("/api/auth/register", json={
        "email": "new_user@property.com",
        "password": "Password123!",
        "full_name": "New Manager",
        "role": "PROPERTY_MANAGER"
    })
    assert res.status_code == 201
    data = res.json()
    assert data["email"] == "new_user@property.com"
    assert data["role"] == "PROPERTY_MANAGER"


def test_register_duplicate_email(client, test_users):
    res = client.post("/api/auth/register", json={
        "email": test_users["manager"].email,
        "password": "Password123!",
        "full_name": "Duplicate Manager",
        "role": "PROPERTY_MANAGER"
    })
    assert res.status_code == 409
    assert "already exists" in res.json()["detail"]


def test_login_success(client, test_users):
    res = client.post("/api/auth/login", json={
        "email": test_users["manager"].email,
        "password": "Pass123!"
    })
    assert res.status_code == 200
    data = res.json()
    assert "access_token" in data
    assert data["user"]["email"] == test_users["manager"].email


def test_login_wrong_password(client, test_users):
    res = client.post("/api/auth/login", json={
        "email": test_users["manager"].email,
        "password": "WrongPassword!"
    })
    assert res.status_code == 401
    assert "Incorrect email or password" in res.json()["detail"]


def test_get_me(client, manager_token, test_users):
    res = client.get("/api/auth/me", headers={"Authorization": f"Bearer {manager_token}"})
    assert res.status_code == 200
    data = res.json()
    assert data["email"] == test_users["manager"].email
    assert data["role"] == "PROPERTY_MANAGER"


def test_get_me_unauthorized(client):
    res = client.get("/api/auth/me")
    assert res.status_code == 401

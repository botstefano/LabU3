def test_login_exitoso(client, admin_user):
    response = client.post("/api/auth/login", json={"email": "admin@test.com", "password": "admin123"})
    assert response.status_code == 200
    body = response.json()
    assert "access_token" in body
    assert body["user"]["email"] == "admin@test.com"


def test_login_credenciales_invalidas(client, admin_user):
    response = client.post("/api/auth/login", json={"email": "admin@test.com", "password": "incorrecta"})
    assert response.status_code == 401


def test_crear_usuario_requiere_admin(client, auth_headers):
    response = client.post(
        "/api/auth/users",
        json={"nombre": "Vendedor Uno", "email": "vendedor@test.com", "password": "clave123", "rol": "vendedor"},
        headers=auth_headers,
    )
    assert response.status_code == 201
    assert response.json()["rol"] == "vendedor"


def test_endpoint_protegido_sin_token(client):
    response = client.get("/api/clients")
    assert response.status_code == 401

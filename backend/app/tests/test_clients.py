def test_crear_cliente_ruc_valido(client, auth_headers):
    response = client.post(
        "/api/clients",
        json={
            "tipo_documento": "RUC",
            "numero_documento": "20123456789",
            "nombre_razon_social": "Comercial Los Andes SAC",
            "direccion": "Av. Peru 123",
            "email": "contacto@losandes.com",
            "telefono": "999888777",
        },
        headers=auth_headers,
    )
    assert response.status_code == 201
    assert response.json()["numero_documento"] == "20123456789"


def test_crear_cliente_ruc_invalido_falla(client, auth_headers):
    response = client.post(
        "/api/clients",
        json={
            "tipo_documento": "RUC",
            "numero_documento": "123",
            "nombre_razon_social": "Cliente Invalido",
        },
        headers=auth_headers,
    )
    assert response.status_code == 422


def test_no_permite_documentos_duplicados(client, auth_headers):
    payload = {
        "tipo_documento": "DNI",
        "numero_documento": "12345678",
        "nombre_razon_social": "Juan Perez",
    }
    primera = client.post("/api/clients", json=payload, headers=auth_headers)
    segunda = client.post("/api/clients", json=payload, headers=auth_headers)
    assert primera.status_code == 201
    assert segunda.status_code == 409

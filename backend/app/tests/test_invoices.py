from datetime import date, timedelta


def _crear_cliente(client, auth_headers):
    response = client.post(
        "/api/clients",
        json={
            "tipo_documento": "RUC",
            "numero_documento": "20111222333",
            "nombre_razon_social": "Distribuidora Central SAC",
        },
        headers=auth_headers,
    )
    return response.json()["id"]


def test_crear_factura_calcula_igv_correctamente(client, auth_headers):
    client_id = _crear_cliente(client, auth_headers)
    vencimiento = (date.today() + timedelta(days=15)).isoformat()

    response = client.post(
        "/api/invoices",
        json={
            "client_id": client_id,
            "fecha_vencimiento": vencimiento,
            "items": [
                {"descripcion": "Servicio de consultoria", "cantidad": 1, "precio_unitario": 100.0},
            ],
        },
        headers=auth_headers,
    )
    assert response.status_code == 201
    data = response.json()
    assert data["subtotal"] == 100.0
    assert data["igv"] == 18.0
    assert data["total"] == 118.0
    assert data["numero"] == 1
    assert data["estado"] == "pendiente"


def test_numeracion_correlativa(client, auth_headers):
    client_id = _crear_cliente(client, auth_headers)
    vencimiento = (date.today() + timedelta(days=10)).isoformat()
    payload = {
        "client_id": client_id,
        "fecha_vencimiento": vencimiento,
        "items": [{"descripcion": "Producto A", "cantidad": 2, "precio_unitario": 50.0}],
    }
    primera = client.post("/api/invoices", json=payload, headers=auth_headers).json()
    segunda = client.post("/api/invoices", json=payload, headers=auth_headers).json()
    assert segunda["numero"] == primera["numero"] + 1


def test_no_permite_vencimiento_en_el_pasado(client, auth_headers):
    client_id = _crear_cliente(client, auth_headers)
    vencimiento = (date.today() - timedelta(days=5)).isoformat()
    response = client.post(
        "/api/invoices",
        json={
            "client_id": client_id,
            "fecha_vencimiento": vencimiento,
            "items": [{"descripcion": "Producto B", "cantidad": 1, "precio_unitario": 30.0}],
        },
        headers=auth_headers,
    )
    assert response.status_code == 422

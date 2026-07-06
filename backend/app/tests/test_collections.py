from datetime import date, timedelta

from app.models.invoice import Invoice


def _crear_factura(client, auth_headers, dias_vencimiento=15, monto=100.0):
    cliente = client.post(
        "/api/clients",
        json={
            "tipo_documento": "DNI",
            "numero_documento": "87654321",
            "nombre_razon_social": "Cliente Cobranza",
        },
        headers=auth_headers,
    ).json()
    vencimiento = (date.today() + timedelta(days=dias_vencimiento)).isoformat()
    factura = client.post(
        "/api/invoices",
        json={
            "client_id": cliente["id"],
            "fecha_vencimiento": vencimiento,
            "items": [{"descripcion": "Producto", "cantidad": 1, "precio_unitario": monto}],
        },
        headers=auth_headers,
    ).json()
    return factura


def test_registrar_pago_completo_marca_factura_pagada(client, auth_headers):
    factura = _crear_factura(client, auth_headers)
    total = factura["total"]

    response = client.post(
        "/api/collections/payments",
        json={"invoice_id": factura["id"], "monto": total, "metodo_pago": "efectivo"},
        headers=auth_headers,
    )
    assert response.status_code == 201

    consulta = client.get(f"/api/invoices/{factura['id']}", headers=auth_headers)
    assert consulta.json()["estado"] == "pagada"


def test_registrar_pago_mayor_al_saldo_falla(client, auth_headers):
    factura = _crear_factura(client, auth_headers)
    response = client.post(
        "/api/collections/payments",
        json={"invoice_id": factura["id"], "monto": factura["total"] + 500, "metodo_pago": "efectivo"},
        headers=auth_headers,
    )
    assert response.status_code == 422


def test_factura_vencida_aparece_en_cartera(client, auth_headers, db_session):
    factura = _crear_factura(client, auth_headers, dias_vencimiento=1)

    # Se simula el paso del tiempo backdateando la fecha de vencimiento
    registro = db_session.get(Invoice, factura["id"])
    registro.fecha_vencimiento = date.today() - timedelta(days=3)
    db_session.commit()

    response = client.get("/api/collections/overdue", headers=auth_headers)
    assert response.status_code == 200
    ids = [item["id"] for item in response.json()]
    assert factura["id"] in ids

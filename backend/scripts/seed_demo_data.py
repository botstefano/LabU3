
"""
Script de siembra (seed) para generar datos de demostración para el sistema de facturación.
Genera clientes, facturas y pagos con diferentes perfiles de pago.

Uso:
    python scripts/seed_demo_data.py
    python scripts/seed_demo_data.py --reset (borra datos de demo primero)
"""

import sys
import random
import uuid
from datetime import datetime, date, timedelta
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))

from sqlalchemy import select, func
from sqlalchemy.orm import Session

from app.db.database import SessionLocal
from app.models.user import User, UserRole
from app.models.client import Client, TipoDocumento
from app.models.invoice import Invoice, InvoiceItem, EstadoFactura
from app.models.payment import Payment
from app.core.config import get_settings

settings = get_settings()
IGV_PORCENTAJE = settings.igv_porcentaje

# Datos de ejemplo para clientes demo
NOMBRES_PERSONAS = [
    "Juan Pérez", "María Gómez", "Carlos Rodríguez", "Ana López", "Luis Fernández",
    "Laura García", "Pedro Martínez", "Sofía Sánchez", "Diego González", "Valentina Ruiz",
    "Jorge Díaz", "Camila Torres", "Mateo Flores", "Isabella Castillo", "Sebastián Cruz",
    "Martina Morales", "Leonardo Ortiz", "Victoria Medina", "Daniel Gutiérrez", "Lucía Romero"
]

NOMBRES_EMPRESAS = [
    "Comercial ABC S.A.C.", "Servicios Integrales E.I.R.L.", "Inversiones XYZ S.R.L.",
    "Tecnología Digital S.A.", "Distribuidora del Sur S.A.C.", "Consultoría Estratégica E.I.R.L.",
    "Constructora Nova S.R.L.", "Importadora Global S.A.", "Agropecuaria Valle S.A.C.",
    "Transporte y Logística E.I.R.L."
]

DESCRIPCIONES_ITEMS = [
    "Consultoría", "Desarrollo de software", "Mantenimiento", "Licencia anual",
    "Servicio de soporte", "Capacitación", "Instalación de equipos", "Reparación",
    "Venta de hardware", "Venta de software"
]


def generar_numero_documento(tipo):
    if tipo == TipoDocumento.DNI:
        return str(random.randint(10000000, 99999999))
    else:
        return "20" + str(random.randint(10000000, 99999999))


def borrar_datos_demo(db: Session):
    """Borra todos los datos de demostración (clientes con prefijo "Demo - ")."""
    clientes_demo = db.scalars(select(Client).where(Client.nombre_razon_social.startswith("Demo - "))).all()
    ids_clientes = [c.id for c in clientes_demo]

    if not ids_clientes:
        return 0

    # Borrar pagos, items, facturas y clientes (en orden)
    db.query(Payment).where(Payment.invoice_id.in_(
        select(Invoice.id).where(Invoice.client_id.in_(ids_clientes))
    )).delete(synchronize_session=False)

    db.query(InvoiceItem).where(InvoiceItem.invoice_id.in_(
        select(Invoice.id).where(Invoice.client_id.in_(ids_clientes))
    )).delete(synchronize_session=False)

    db.query(Invoice).where(Invoice.client_id.in_(ids_clientes)).delete(synchronize_session=False)

    db.query(Client).where(Client.id.in_(ids_clientes)).delete(synchronize_session=False)

    db.commit()
    return len(ids_clientes)


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Genera datos de demostración para el sistema de facturación.")
    parser.add_argument("--reset", action="store_true", help="Borra los datos de demo existentes primero.")
    args = parser.parse_args()

    db = SessionLocal()
    try:
        # Verificar que exista un usuario administrador
        admin_user = db.scalars(select(User).where(User.rol == UserRole.ADMINISTRADOR)).first()
        if not admin_user:
            print("Error: No existe un usuario administrador. Ejecuta primero 'python scripts/seed_admin.py'.")
            return

        if args.reset:
            print("Borrando datos de demostración existentes...")
            count = borrar_datos_demo(db)
            print(f"Se borraron {count} clientes de demostración y sus datos asociados.")

        # Verificar que no existan ya datos de demo
        clientes_existentes = db.scalars(select(Client).where(Client.nombre_razon_social.startswith("Demo - "))).count()
        if clientes_existentes > 0:
            print("Ya existen datos de demostración. Usa --reset para borrar y regenerar.")
            return

        print("Generando datos de demostración...")

        # Obtener próximo número de factura
        max_numero = db.scalar(select(func.max(Invoice.numero)).where(Invoice.serie == "F001")) or 0
        next_numero = max_numero + 1

        # Generar clientes (30 total)
        total_clientes = 30
        buenos_pagadores = int(total_clientes * 0.4)  # 40%
        pagadores_intermedios = int(total_clientes * 0.35)  # 35%
        malos_pagadores = int(total_clientes * 0.25)  # 25%

        clientes = []
        for i in range(total_clientes):
            if i < buenos_pagadores:
                perfil = "buen"
            elif i < buenos_pagadores + pagadores_intermedios:
                perfil = "intermedio"
            else:
                perfil = "malo"

            if random.random() < 0.6:  # 60% personas, 40% empresas
                tipo_doc = TipoDocumento.DNI
                nombre = random.choice(NOMBRES_PERSONAS)
            else:
                tipo_doc = TipoDocumento.RUC
                nombre = random.choice(NOMBRES_EMPRESAS)

            numero_doc = generar_numero_documento(tipo_doc)
            while db.scalar(select(Client).where(Client.numero_documento == numero_doc)):
                numero_doc = generar_numero_documento(tipo_doc)

            cliente = Client(
                tipo_documento=tipo_doc,
                numero_documento=numero_doc,
                nombre_razon_social=f"Demo - {nombre}",
                direccion=f"Av. {random.choice(['San Juan', 'Principal', 'Los Olivos', 'Javier Prado', 'Arequipa'])} {random.randint(100, 9999)}, Lima",
                email=f"demo.{uuid.uuid4().hex[:8]}@example.com",
                telefono=f"9{random.randint(10000000, 99999999)}",
                created_at=datetime.utcnow() - timedelta(days=random.randint(30, 365))
            )
            cliente._perfil = perfil  # atributo temporal para generar datos
            clientes.append(cliente)
            db.add(cliente)

        db.commit()
        for cliente in clientes:
            db.refresh(cliente)

        # Generar facturas y pagos para cada cliente
        facturas_por_estado = {estado: 0 for estado in EstadoFactura}
        total_facturas = 0

        for cliente in clientes:
            num_facturas = random.randint(2, 8)
            for _ in range(num_facturas):
                # Fechas de emisión en los últimos 6 meses
                dias_atras = random.randint(0, 180)
                fecha_emision = date.today() - timedelta(days=dias_atras)
                fecha_vencimiento = fecha_emision + timedelta(days=random.randint(7, 30))

                # Crear items
                num_items = random.randint(1, 4)
                items = []
                subtotal_total = 0.0
                for _ in range(num_items):
                    descripcion = random.choice(DESCRIPCIONES_ITEMS)
                    cantidad = random.uniform(1, 10)
                    precio_unitario = random.uniform(50, 2000)
                    subtotal = round(cantidad * precio_unitario, 2)
                    subtotal_total += subtotal
                    items.append(InvoiceItem(
                        descripcion=descripcion,
                        cantidad=cantidad,
                        precio_unitario=precio_unitario,
                        subtotal=subtotal
                    ))

                subtotal_total = round(subtotal_total, 2)
                igv = round(subtotal_total * (IGV_PORCENTAJE / 100), 2)
                total = round(subtotal_total + igv, 2)

                # Determinar estado de la factura y pagos
                estado = EstadoFactura.PENDIENTE
                fecha_pago = None

                if cliente._perfil == "buen":
                    # 90% pagadas, 10% pendientes (dentro de plazo)
                    if random.random() < 0.9:
                        estado = EstadoFactura.PAGADA
                        # Pago a tiempo o unos días después máximo
                        dias_pago = random.randint(-2, 2)
                        fecha_pago = fecha_vencimiento + timedelta(days=dias_pago)
                elif cliente._perfil == "intermedio":
                    # 50% pagadas (algunas con mora moderada), 30% vencidas, 20% pendientes
                    r = random.random()
                    if r < 0.5:
                        estado = EstadoFactura.PAGADA
                        dias_pago = random.randint(0, 30)
                        fecha_pago = fecha_vencimiento + timedelta(days=dias_pago)
                    elif r < 0.8:
                        estado = EstadoFactura.VENCIDA
                else:  # malo
                    # 20% pagadas (mucha mora), 60% vencidas, 20% pendientes
                    r = random.random()
                    if r < 0.2:
                        estado = EstadoFactura.PAGADA
                        dias_pago = random.randint(30, 90)
                        fecha_pago = fecha_vencimiento + timedelta(days=dias_pago)
                    elif r < 0.8:
                        estado = EstadoFactura.VENCIDA

                # Si la factura está pendiente pero ya venció, cambiar estado
                if estado == EstadoFactura.PENDIENTE and date.today() > fecha_vencimiento:
                    estado = EstadoFactura.VENCIDA

                factura = Invoice(
                    serie="F001",
                    numero=next_numero,
                    client_id=cliente.id,
                    fecha_emision=fecha_emision,
                    fecha_vencimiento=fecha_vencimiento,
                    subtotal=subtotal_total,
                    igv=igv,
                    total=total,
                    estado=estado,
                    created_by=admin_user.id,
                    created_at=datetime.combine(fecha_emision, datetime.min.time()),
                    items=items
                )
                db.add(factura)
                next_numero += 1
                total_facturas += 1
                facturas_por_estado[estado] += 1

                if estado == EstadoFactura.PAGADA and fecha_pago:
                    pago = Payment(
                        invoice_id=factura.id,
                        fecha_pago=fecha_pago if fecha_pago <= date.today() else date.today(),
                        monto=total,
                        metodo_pago=random.choice(["transferencia", "efectivo", "tarjeta"]),
                        registrado_por=admin_user.id,
                        created_at=datetime.combine(fecha_pago if fecha_pago <= date.today() else date.today(), datetime.min.time())
                    )
                    db.add(pago)

        db.commit()

        print("\n✅ Datos de demostración generados exitosamente!")
        print(f"Clientes creados: {total_clientes}")
        print(f"Facturas creadas: {total_facturas}")
        for estado, count in facturas_por_estado.items():
            print(f"  - {estado}: {count}")
        print("\nAhora puedes:")
        print("1. Ejecutar el backend: uvicorn app.main:app --reload")
        print("2. Ir a /riesgo en el frontend")
        print("3. Hacer clic en 'Entrenar Modelo' para entrenar el modelo de riesgo")

    finally:
        db.close()


if __name__ == "__main__":
    main()


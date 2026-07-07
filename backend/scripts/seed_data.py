"""
Script de poblacion completa para el sistema de facturacion electronica.
Crea usuarios, clientes, facturas, items y pagos de ejemplo.

Uso:
    python scripts/seed_data.py
"""
import sys
from pathlib import Path
from datetime import date, datetime, timedelta
import uuid

sys.path.append(str(Path(__file__).resolve().parent.parent))

from app.core.security import hash_password
from app.db.database import SessionLocal
from app.models.user import User, UserRole
from app.models.client import Client, TipoDocumento
from app.models.invoice import Invoice, InvoiceItem, EstadoFactura
from app.models.payment import Payment


def seed_users(db):
    """Crear usuarios de ejemplo"""
    print("Creando usuarios...")
    
    users_data = [
        {
            "nombre": "Carlos Administrador",
            "email": "admin@empresa.com",
            "password": "admin123",
            "rol": UserRole.ADMINISTRADOR
        },
        {
            "nombre": "Maria Contadora",
            "email": "contador@empresa.com",
            "password": "contador123",
            "rol": UserRole.CONTADOR
        },
        {
            "nombre": "Juan Vendedor",
            "email": "vendedor@empresa.com",
            "password": "vendedor123",
            "rol": UserRole.VENDEDOR
        },
        {
            "nombre": "Ana Vendedora",
            "email": "ana@empresa.com",
            "password": "ana123",
            "rol": UserRole.VENDEDOR
        }
    ]
    
    users = {}
    for user_data in users_data:
        existing = db.query(User).filter(User.email == user_data["email"]).first()
        if not existing:
            user = User(
                nombre=user_data["nombre"],
                email=user_data["email"],
                password_hash=hash_password(user_data["password"]),
                rol=user_data["rol"],
                activo=True
            )
            db.add(user)
            db.flush()
            users[user_data["rol"]] = user
            print(f"  - {user_data['nombre']} ({user_data['rol'].value})")
        else:
            users[user_data["rol"]] = existing
            print(f"  - {user_data['nombre']} ya existe")
    
    db.commit()
    return users


def seed_clients(db):
    """Crear clientes de ejemplo"""
    print("Creando clientes...")
    
    clients_data = [
        {
            "tipo_documento": TipoDocumento.RUC,
            "numero_documento": "20123456789",
            "nombre_razon_social": "Inversiones Generales S.A.C.",
            "direccion": "Av. Principal 123, Lima",
            "email": "contacto@inversiones.com",
            "telefono": "01-555-1234"
        },
        {
            "tipo_documento": TipoDocumento.RUC,
            "numero_documento": "20567890123",
            "nombre_razon_social": "Comercializadora del Norte E.I.R.L.",
            "direccion": "Jr. Comercio 456, Trujillo",
            "email": "ventas@comercializadora.com",
            "telefono": "044-123-456"
        },
        {
            "tipo_documento": TipoDocumento.DNI,
            "numero_documento": "12345678",
            "nombre_razon_social": "Pedro Perez Lopez",
            "direccion": "Calle Los Olivos 789, Lima",
            "email": "pedro.perez@gmail.com",
            "telefono": "999-888-777"
        },
        {
            "tipo_documento": TipoDocumento.RUC,
            "numero_documento": "20678901234",
            "nombre_razon_social": "Tecnologia Avanzada S.A.",
            "direccion": "Av. Industrial 321, Arequipa",
            "email": "info@tecnologiaavanzada.com",
            "telefono": "054-456-789"
        },
        {
            "tipo_documento": TipoDocumento.DNI,
            "numero_documento": "87654321",
            "nombre_razon_social": "Luisa Martinez Sanchez",
            "direccion": "Av. Brasil 654, Lima",
            "email": "luisa.martinez@yahoo.com",
            "telefono": "999-777-888"
        },
        {
            "tipo_documento": TipoDocumento.RUC,
            "numero_documento": "20901234567",
            "nombre_razon_social": "Constructora del Sur S.A.C.",
            "direccion": "Av. Sur 987, Cusco",
            "email": "proyectos@constructorasur.com",
            "telefono": "084-234-567"
        },
        {
            "tipo_documento": TipoDocumento.DNI,
            "numero_documento": "45678901",
            "nombre_razon_social": "Roberto Garcia Torres",
            "direccion": "Calle San Martin 123, Piura",
            "email": "roberto.garcia@hotmail.com",
            "telefono": "999-666-555"
        },
        {
            "tipo_documento": TipoDocumento.RUC,
            "numero_documento": "20345678901",
            "nombre_razon_social": "Importadora Global E.I.R.L.",
            "direccion": "Av. Espana 456, Chiclayo",
            "email": "ventas@importadoraglobal.com",
            "telefono": "074-345-678"
        }
    ]
    
    clients = []
    for client_data in clients_data:
        existing = db.query(Client).filter(Client.numero_documento == client_data["numero_documento"]).first()
        if not existing:
            client = Client(**client_data)
            db.add(client)
            db.flush()
            clients.append(client)
            print(f"  - {client_data['nombre_razon_social']}")
        else:
            clients.append(existing)
            print(f"  - {client_data['nombre_razon_social']} ya existe")
    
    db.commit()
    return clients


def seed_invoices_and_payments(db, clients, users):
    """Crear facturas y pagos de ejemplo"""
    print("Creando facturas y pagos...")
    
    vendedor = users.get(UserRole.VENDEDOR)
    contador = users.get(UserRole.CONTADOR)
    
    invoices_data = [
        {
            "client": clients[0],
            "serie": "F001",
            "numero": 1,
            "fecha_emision": date.today() - timedelta(days=30),
            "fecha_vencimiento": date.today() - timedelta(days=15),
            "estado": EstadoFactura.PAGADA,
            "items": [
                {"descripcion": "Laptop HP ProBook", "cantidad": 5, "precio_unitario": 3500.00},
                {"descripcion": "Monitor LG 24 pulgadas", "cantidad": 5, "precio_unitario": 450.00}
            ],
            "payment": {
                "fecha_pago": date.today() - timedelta(days=20),
                "monto": 23310.00,
                "metodo_pago": "transferencia"
            }
        },
        {
            "client": clients[1],
            "serie": "F001",
            "numero": 2,
            "fecha_emision": date.today() - timedelta(days=25),
            "fecha_vencimiento": date.today() - timedelta(days=10),
            "estado": EstadoFactura.PAGADA,
            "items": [
                {"descripcion": "Escritorio ergonómico", "cantidad": 10, "precio_unitario": 850.00},
                {"descripcion": "Silla ejecutiva", "cantidad": 10, "precio_unitario": 650.00}
            ],
            "payment": {
                "fecha_pago": date.today() - timedelta(days=15),
                "monto": 17700.00,
                "metodo_pago": "transferencia"
            }
        },
        {
            "client": clients[2],
            "serie": "F001",
            "numero": 3,
            "fecha_emision": date.today() - timedelta(days=20),
            "fecha_vencimiento": date.today() + timedelta(days=5),
            "estado": EstadoFactura.PENDIENTE,
            "items": [
                {"descripcion": "Impresora multifuncional Epson", "cantidad": 1, "precio_unitario": 1200.00},
                {"descripcion": "Cartuchos de tinta (pack)", "cantidad": 2, "precio_unitario": 350.00}
            ],
            "payment": None
        },
        {
            "client": clients[3],
            "serie": "F001",
            "numero": 4,
            "fecha_emision": date.today() - timedelta(days=15),
            "fecha_vencimiento": date.today() - timedelta(days=2),
            "estado": EstadoFactura.VENCIDA,
            "items": [
                {"descripcion": "Servidor Dell PowerEdge", "cantidad": 2, "precio_unitario": 8500.00},
                {"descripcion": "RAID Controller", "cantidad": 2, "precio_unitario": 1200.00}
            ],
            "payment": None
        },
        {
            "client": clients[4],
            "serie": "F001",
            "numero": 5,
            "fecha_emision": date.today() - timedelta(days=10),
            "fecha_vencimiento": date.today() + timedelta(days=20),
            "estado": EstadoFactura.PENDIENTE,
            "items": [
                {"descripcion": "Tablet iPad Pro", "cantidad": 3, "precio_unitario": 4200.00},
                {"descripcion": "Apple Pencil", "cantidad": 3, "precio_unitario": 350.00}
            ],
            "payment": None
        },
        {
            "client": clients[5],
            "serie": "F001",
            "numero": 6,
            "fecha_emision": date.today() - timedelta(days=5),
            "fecha_vencimiento": date.today() + timedelta(days=25),
            "estado": EstadoFactura.PENDIENTE,
            "items": [
                {"descripcion": "Proyector Epson", "cantidad": 1, "precio_unitario": 2800.00},
                {"descripcion": "Pantalla de proyección", "cantidad": 1, "precio_unitario": 650.00}
            ],
            "payment": None
        },
        {
            "client": clients[6],
            "serie": "F001",
            "numero": 7,
            "fecha_emision": date.today(),
            "fecha_vencimiento": date.today() + timedelta(days=30),
            "estado": EstadoFactura.PENDIENTE,
            "items": [
                {"descripcion": "Smartphone Samsung Galaxy", "cantidad": 2, "precio_unitario": 3200.00},
                {"descripcion": "Fundas protectoras", "cantidad": 2, "precio_unitario": 80.00}
            ],
            "payment": None
        },
        {
            "client": clients[7],
            "serie": "F001",
            "numero": 8,
            "fecha_emision": date.today() - timedelta(days=35),
            "fecha_vencimiento": date.today() - timedelta(days=20),
            "estado": EstadoFactura.ANULADA,
            "items": [
                {"descripcion": "Laptop Lenovo ThinkPad", "cantidad": 3, "precio_unitario": 3800.00}
            ],
            "payment": None
        }
    ]
    
    igv_porcentaje = 0.18
    
    for invoice_data in invoices_data:
        # Verificar si ya existe
        existing = db.query(Invoice).filter(
            Invoice.serie == invoice_data["serie"],
            Invoice.numero == invoice_data["numero"]
        ).first()
        
        if existing:
            print(f"  - Factura {invoice_data['serie']}-{invoice_data['numero']} ya existe")
            continue
        
        # Calcular totales
        subtotal = sum(item["cantidad"] * item["precio_unitario"] for item in invoice_data["items"])
        igv = subtotal * igv_porcentaje
        total = subtotal + igv
        
        # Crear factura
        invoice = Invoice(
            serie=invoice_data["serie"],
            numero=invoice_data["numero"],
            client_id=invoice_data["client"].id,
            fecha_emision=invoice_data["fecha_emision"],
            fecha_vencimiento=invoice_data["fecha_vencimiento"],
            subtotal=subtotal,
            igv=igv,
            total=total,
            estado=invoice_data["estado"],
            created_by=vendedor.id if vendedor else users[UserRole.ADMINISTRADOR].id
        )
        db.add(invoice)
        db.flush()
        
        # Crear items
        for item_data in invoice_data["items"]:
            item_subtotal = item_data["cantidad"] * item_data["precio_unitario"]
            item = InvoiceItem(
                invoice_id=invoice.id,
                descripcion=item_data["descripcion"],
                cantidad=item_data["cantidad"],
                precio_unitario=item_data["precio_unitario"],
                subtotal=item_subtotal
            )
            db.add(item)
        
        # Crear pago si existe
        if invoice_data["payment"]:
            payment = Payment(
                invoice_id=invoice.id,
                fecha_pago=invoice_data["payment"]["fecha_pago"],
                monto=invoice_data["payment"]["monto"],
                metodo_pago=invoice_data["payment"]["metodo_pago"],
                registrado_por=contador.id if contador else users[UserRole.ADMINISTRADOR].id
            )
            db.add(payment)
        
        print(f"  - Factura {invoice_data['serie']}-{invoice_data['numero']} ({invoice_data['estado'].value}) - S/ {total:.2f}")
    
    db.commit()


def seed_app_settings(db):
    """Crear configuracion de la aplicacion"""
    print("Creando configuracion de la aplicacion...")
    
    settings_data = [
        {"clave": "empresa_razon_social", "valor": "Mi Empresa S.A.C."},
        {"clave": "empresa_ruc", "valor": "20123456789"},
        {"clave": "empresa_direccion", "valor": "Av. Principal 123, Lima, Peru"},
        {"clave": "empresa_telefono", "valor": "01-555-1234"},
        {"clave": "empresa_email", "valor": "contacto@miempresa.com"},
        {"clave": "igv_porcentaje", "valor": "18"},
        {"clave": "factura_serie", "valor": "F001"},
        {"clave": "factura_correlativo", "valor": "100"},
        {"clave": "moneda", "valor": "PEN"}
    ]
    
    from app.models.settings_model import AppSetting
    
    for setting_data in settings_data:
        existing = db.query(AppSetting).filter(AppSetting.clave == setting_data["clave"]).first()
        if not existing:
            setting = AppSetting(**setting_data)
            db.add(setting)
            print(f"  - {setting_data['clave']}: {setting_data['valor']}")
    
    db.commit()


def main():
    db = SessionLocal()
    try:
        print("=== Iniciando poblacion de datos ===\n")
        
        # Crear usuarios
        users = seed_users(db)
        print()
        
        # Crear clientes
        clients = seed_clients(db)
        print()
        
        # Crear facturas y pagos
        seed_invoices_and_payments(db, clients, users)
        print()
        
        # Crear configuracion
        seed_app_settings(db)
        print()
        
        print("=== Poblacion completada exitosamente ===")
        print("\nUsuarios de prueba:")
        print("  - admin@empresa.com / admin123 (Administrador)")
        print("  - contador@empresa.com / contador123 (Contador)")
        print("  - vendedor@empresa.com / vendedor123 (Vendedor)")
        print("  - ana@empresa.com / ana123 (Vendedor)")
        
    except Exception as e:
        print(f"Error durante la poblacion: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()

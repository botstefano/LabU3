"""
Servicio de negocio del módulo de cuentas por cobrar / morosidad.

Gestiona el registro de pagos, el cálculo de días de mora y la
segmentación de deuda por antigüedad (aging de cartera).
"""
import uuid

from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, NotFoundError, ValidationAppError
from app.models.invoice import EstadoFactura
from app.models.payment import Payment
from app.repositories.invoice_repository import InvoiceRepository
from app.repositories.payment_repository import PaymentRepository
from app.schemas.payment import DebtSegment, OverdueInvoice, PaymentCreate
from app.services.invoice_service import InvoiceService


class CollectionsService:
    def __init__(self, db: Session):
        self.db = db
        self.invoice_repo = InvoiceRepository(db)
        self.payment_repo = PaymentRepository(db)
        self.invoice_service = InvoiceService(db)

    def registrar_pago(self, data: PaymentCreate, registrado_por: uuid.UUID) -> Payment:
        invoice = self.invoice_repo.get_by_id(data.invoice_id)
        if not invoice:
            raise NotFoundError("Factura no encontrada")
        if invoice.estado == EstadoFactura.ANULADA:
            raise ConflictError("No se puede registrar pagos sobre una factura anulada")

        saldo = self.invoice_service.saldo_pendiente(invoice)
        if data.monto > saldo + 0.01:
            raise ValidationAppError(f"El monto excede el saldo pendiente (S/ {saldo:.2f})")

        payment = Payment(
            invoice_id=data.invoice_id,
            monto=data.monto,
            metodo_pago=data.metodo_pago,
            fecha_pago=data.fecha_pago,
            registrado_por=registrado_por,
        )
        self.payment_repo.create(payment)

        nuevo_saldo = self.invoice_service.saldo_pendiente(invoice)
        if nuevo_saldo <= 0.01:
            invoice.estado = EstadoFactura.PAGADA
            self.invoice_repo.update(invoice)

        return payment

    def cartera_vencida(self) -> list[OverdueInvoice]:
        self.invoice_service.actualizar_estados_vencidos()
        resultado = []
        for invoice in self.invoice_repo.list_pendientes_vencidas():
            dias = self.invoice_service.dias_mora(invoice)
            if dias <= 0:
                continue
            resultado.append(
                OverdueInvoice(
                    id=invoice.id,
                    serie=invoice.serie,
                    numero=invoice.numero,
                    cliente_nombre=invoice.client.nombre_razon_social,
                    fecha_vencimiento=invoice.fecha_vencimiento,
                    dias_mora=dias,
                    total=float(invoice.total),
                    saldo_pendiente=self.invoice_service.saldo_pendiente(invoice),
                )
            )
        return sorted(resultado, key=lambda x: x.dias_mora, reverse=True)

    def segmentacion_deuda(self) -> list[DebtSegment]:
        vencidas = self.cartera_vencida()
        rangos = [
            ("1-15 dias", 1, 15),
            ("16-30 dias", 16, 30),
            ("31-60 dias", 31, 60),
            ("Mas de 60 dias", 61, 10_000),
        ]
        segmentos = []
        for nombre, minimo, maximo in rangos:
            en_rango = [f for f in vencidas if minimo <= f.dias_mora <= maximo]
            segmentos.append(
                DebtSegment(
                    segmento=nombre,
                    cantidad_facturas=len(en_rango),
                    monto_total=round(sum(f.saldo_pendiente for f in en_rango), 2),
                )
            )
        return segmentos

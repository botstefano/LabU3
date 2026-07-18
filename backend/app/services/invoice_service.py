"""
Servicio de negocio de facturación.

Encapsula el cálculo automático de IGV, la numeración correlativa de
comprobantes y las transiciones de estado de una factura.
"""
import uuid
from datetime import date
from typing import Tuple, Optional

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.exceptions import ConflictError, NotFoundError, ValidationAppError
from app.models.invoice import EstadoFactura, Invoice, InvoiceItem
from app.repositories.client_repository import ClientRepository
from app.repositories.invoice_repository import InvoiceRepository
from app.repositories.payment_repository import PaymentRepository
from app.repositories.settings_repository import SettingsRepository
from app.schemas.invoice import InvoiceCreate
from app.services.risk_service import RiskService

settings = get_settings()


class InvoiceService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = InvoiceRepository(db)
        self.client_repo = ClientRepository(db)
        self.payment_repo = PaymentRepository(db)
        self.settings_repo = SettingsRepository(db)
        self.risk_service = RiskService(db)

    def _igv_porcentaje(self) -> float:
        valores = self.settings_repo.get_all()
        raw = valores.get("igv_porcentaje")
        try:
            return float(raw) if raw else settings.igv_porcentaje
        except (TypeError, ValueError):
            return settings.igv_porcentaje

    def create(self, data: InvoiceCreate, created_by: uuid.UUID) -> Tuple[Invoice, Optional[dict]]:
        client = self.client_repo.get_by_id(data.client_id)
        if not client:
            raise NotFoundError("Cliente no encontrado")
        if data.fecha_vencimiento < date.today():
            raise ValidationAppError("La fecha de vencimiento no puede ser anterior a hoy")

        igv_pct = self._igv_porcentaje()
        items = []
        subtotal_total = 0.0
        for item in data.items:
            item_subtotal = round(item.cantidad * item.precio_unitario, 2)
            subtotal_total += item_subtotal
            items.append(
                InvoiceItem(
                    descripcion=item.descripcion,
                    cantidad=item.cantidad,
                    precio_unitario=item.precio_unitario,
                    subtotal=item_subtotal,
                )
            )

        igv = round(subtotal_total * (igv_pct / 100), 2)
        total = round(subtotal_total + igv, 2)
        numero = self.repo.next_numero()

        invoice = Invoice(
            serie="F001",
            numero=numero,
            client_id=data.client_id,
            fecha_emision=date.today(),
            fecha_vencimiento=data.fecha_vencimiento,
            subtotal=subtotal_total,
            igv=igv,
            total=total,
            estado=EstadoFactura.PENDIENTE,
            created_by=created_by,
            items=items,
        )
        
        created_invoice = self.repo.create(invoice)
        
        # Calcular riesgo del cliente automáticamente
        riesgo_alerta = None
        try:
            riesgo = self.risk_service.score_client(data.client_id)
            if riesgo.score > 0.7:  # Riesgo alto (>70%)
                riesgo_alerta = {
                    "nivel": riesgo.nivel,
                    "score": riesgo.score,
                    "mensaje": f"⚠️ Cliente con alto riesgo de morosidad ({riesgo.score*100:.0f}%)",
                    "factores": {
                        "pct_facturas_vencidas": riesgo.factores.pct_facturas_vencidas,
                        "pct_pagos_tardios": riesgo.factores.pct_pagos_tardios,
                        "dias_mora_promedio": riesgo.factores.dias_mora_promedio
                    }
                }
        except Exception:
            # Si no se puede calcular riesgo, continuar sin alerta
            pass
        
        return created_invoice, riesgo_alerta

    def get(self, invoice_id: uuid.UUID) -> Invoice:
        invoice = self.repo.get_by_id(invoice_id)
        if not invoice:
            raise NotFoundError("Factura no encontrada")
        return invoice

    def list(self, **filters):
        return self.repo.list(**filters)

    def anular(self, invoice_id: uuid.UUID) -> Invoice:
        invoice = self.get(invoice_id)
        if invoice.estado == EstadoFactura.PAGADA:
            raise ConflictError("No se puede anular una factura ya pagada")
        invoice.estado = EstadoFactura.ANULADA
        return self.repo.update(invoice)

    def saldo_pendiente(self, invoice: Invoice) -> float:
        pagado = self.payment_repo.total_pagado(invoice.id)
        return round(float(invoice.total) - pagado, 2)

    def dias_mora(self, invoice: Invoice) -> int:
        if invoice.estado in (EstadoFactura.PAGADA, EstadoFactura.ANULADA):
            return 0
        delta = date.today() - invoice.fecha_vencimiento
        return max(delta.days, 0)

    def actualizar_estados_vencidos(self) -> None:
        """Recalcula el estado de facturas pendientes que ya vencieron."""
        for invoice in self.repo.list_pendientes_vencidas():
            if invoice.estado == EstadoFactura.PENDIENTE and date.today() > invoice.fecha_vencimiento:
                invoice.estado = EstadoFactura.VENCIDA
        self.db.commit()

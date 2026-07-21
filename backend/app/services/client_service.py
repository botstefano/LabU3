"""Servicio de negocio para la gestión de clientes (CRUD y validaciones)."""
import uuid
from datetime import date
from typing import Optional, List, Dict, Any

from sqlalchemy import func, and_
from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, NotFoundError
from app.models.client import Client
from app.models.invoice import Invoice, EstadoFactura
from app.models.payment import Payment
from app.repositories.client_repository import ClientRepository
from app.schemas.client import ClientCreate, ClientUpdate


class ClientService:
    def __init__(self, db: Session):
        self.repo = ClientRepository(db)
        self.db = db

    def _calcular_riesgo_heuristico(self, client_id: uuid.UUID) -> Dict[str, Any]:
        """Calcula riesgo heurístico basado en reglas simples usando datos históricos del cliente."""
        # Obtener todas las facturas del cliente
        facturas = self.db.scalars(
            select(Invoice).where(Invoice.client_id == client_id)
        ).all()

        if not facturas:
            return {
                "nivel": "sin_datos",
                "score": 0.5,
                "factores": {
                    "pct_facturas_vencidas": 0.0,
                    "pct_pagos_tardios": 0.0,
                    "dias_mora_promedio": 0.0,
                    "monto_total_deuda": 0.0
                },
                "justificacion": "Cliente sin historial de facturas"
            }

        # Calcular métricas
        total_facturas = len(facturas)
        facturas_vencidas = sum(1 for f in facturas if f.estado == EstadoFactura.VENCIDA)
        facturas_pagadas = sum(1 for f in facturas if f.estado == EstadoFactura.PAGADA)

        # Calcular pagos tardíos (pagados después de la fecha de vencimiento)
        pagos_tardios = 0
        dias_mora_total = 0
        total_deuda = 0.0

        for factura in facturas:
            if factura.estado == EstadoFactura.PENDIENTE or factura.estado == EstadoFactura.VENCIDA:
                total_deuda += float(factura.total)
            elif factura.estado == EstadoFactura.PAGADA:
                # Verificar si se pagó tarde
                pago = self.db.scalar(
                    select(Payment).where(Payment.invoice_id == factura.id)
                )
                if pago and pago.fecha_pago > factura.fecha_vencimiento:
                    pagos_tardios += 1
                    dias_mora_total += (pago.fecha_pago - factura.fecha_vencimiento).days
                elif factura.fecha_vencimiento < date.today():
                    # Si está pagada pero la fecha de pago no está registrada, asumir que fue tardía si venció
                    pagos_tardios += 1
                    dias_mora_total += (date.today() - factura.fecha_vencimiento).days

        # Calcular porcentajes
        pct_facturas_vencidas = facturas_vencidas / total_facturas if total_facturas > 0 else 0.0
        pct_pagos_tardios = pagos_tardios / facturas_pagadas if facturas_pagadas > 0 else 0.0
        dias_mora_promedio = dias_mora_total / pagos_tardios if pagos_tardios > 0 else 0.0

        # Calcular score de riesgo (0 = bajo riesgo, 1 = alto riesgo)
        # Pesos: 40% facturas vencidas, 30% pagos tardíos, 20% días mora, 10% deuda
        score_riesgo = (
            pct_facturas_vencidas * 0.4 +
            pct_pagos_tardios * 0.3 +
            min(dias_mora_promedio / 60, 1.0) * 0.2 +
            min(total_deuda / 10000, 1.0) * 0.1
        )

        # Determinar nivel de riesgo
        if score_riesgo < 0.25:
            nivel = "bajo"
        elif score_riesgo < 0.5:
            nivel = "medio"
        elif score_riesgo < 0.75:
            nivel = "alto"
        else:
            nivel = "muy_alto"

        # Generar justificación
        razones = []
        if pct_facturas_vencidas > 0.3:
            razones.append(f"alto porcentaje de facturas vencidas ({pct_facturas_vencidas*100:.1f}%)")
        if pct_pagos_tardios > 0.3:
            razones.append(f"alto porcentaje de pagos tardíos ({pct_pagos_tardios*100:.1f}%)")
        if dias_mora_promedio > 30:
            razones.append(f"mora promedio alta ({dias_mora_promedio:.1f} días)")
        if total_deuda > 5000:
            razones.append(f"deuda significativa (S/ {total_deuda:.2f})")

        justificacion = ". ".join(razones) if razones else "Historial de pagos favorable"

        return {
            "nivel": nivel,
            "score": round(score_riesgo, 3),
            "factores": {
                "pct_facturas_vencidas": round(pct_facturas_vencidas, 3),
                "pct_pagos_tardios": round(pct_pagos_tardios, 3),
                "dias_mora_promedio": round(dias_mora_promedio, 1),
                "monto_total_deuda": round(total_deuda, 2)
            },
            "justificacion": justificacion
        }

    def create(self, data: ClientCreate) -> Client:
        if self.repo.get_by_documento(data.numero_documento):
            raise ConflictError("Ya existe un cliente con ese numero de documento")
        client = Client(**data.model_dump())
        return self.repo.create(client)

    def get(self, client_id: uuid.UUID) -> Client:
        client = self.repo.get_by_id(client_id)
        if not client:
            raise NotFoundError("Cliente no encontrado")
        return client

    def list(self, search: Optional[str], skip: int, limit: int):
        clients = self.repo.list(search=search, skip=skip, limit=limit)
        # Agregar riesgo heurístico a cada cliente
        result = []
        for client in clients:
            client_dict = {
                "id": client.id,
                "tipo_documento": client.tipo_documento,
                "numero_documento": client.numero_documento,
                "nombre_razon_social": client.nombre_razon_social,
                "direccion": client.direccion,
                "email": client.email,
                "telefono": client.telefono,
                "created_at": client.created_at,
                "riesgo_heuristico": self._calcular_riesgo_heuristico(client.id)
            }
            result.append(client_dict)
        return result

    def update(self, client_id: uuid.UUID, data: ClientUpdate) -> Client:
        client = self.get(client_id)
        existing = self.repo.get_by_documento(data.numero_documento)
        if existing and existing.id != client.id:
            raise ConflictError("Ya existe otro cliente con ese numero de documento")
        for field, value in data.model_dump().items():
            setattr(client, field, value)
        return self.repo.update(client)

    def delete(self, client_id: uuid.UUID) -> None:
        client = self.get(client_id)
        self.repo.delete(client)

"""Servicio de negocio para las métricas del dashboard analítico."""
from collections import defaultdict
from datetime import date
import logging

from sqlalchemy.orm import Session

from app.models.invoice import EstadoFactura
from app.repositories.invoice_repository import InvoiceRepository
from app.schemas.dashboard import DashboardResponse, FacturacionMensual, TopCliente
from app.services.collections_service import CollectionsService

logger = logging.getLogger(__name__)

MESES = [
    "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
    "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre",
]


class DashboardService:
    def __init__(self, db: Session):
        self.db = db
        self.invoice_repo = InvoiceRepository(db)
        self.collections_service = CollectionsService(db)

    def resumen(self) -> DashboardResponse:
        hoy = date.today()
        inicio_anio = date(hoy.year, 1, 1)
        facturas_anio = [
            f for f in self.invoice_repo.list_all_in_range(inicio_anio, hoy) if str(f.estado) != "ANULADA"
        ]

        # Debug logging
        logger.warning(f"Total facturas anio: {len(facturas_anio)}")
        for f in facturas_anio:
            logger.warning(f"Factura {f.serie}-{f.numero}: estado={f.estado}, str_estado={str(f.estado)}")

        facturas_mes_actual = [f for f in facturas_anio if f.fecha_emision.month == hoy.month]
        total_facturado_mes = round(sum(float(f.total) for f in facturas_mes_actual), 2)
        igv_mes = round(sum(float(f.igv) for f in facturas_mes_actual), 2)

        cartera_vencida = self.collections_service.cartera_vencida()
        total_morosidad = round(sum(f.saldo_pendiente for f in cartera_vencida), 2)

        facturas_pendientes = [f for f in facturas_anio if str(f.estado) in ("PENDIENTE", "VENCIDA")]
        logger.warning(f"Facturas pendientes: {len(facturas_pendientes)}")

        por_mes = defaultdict(lambda: {"total": 0.0, "igv": 0.0})
        for factura in facturas_anio:
            key = factura.fecha_emision.month
            por_mes[key]["total"] += float(factura.total)
            por_mes[key]["igv"] += float(factura.igv)

        facturacion_mensual = [
            FacturacionMensual(
                mes=MESES[mes - 1],
                total_facturado=round(datos["total"], 2),
                igv_recaudado=round(datos["igv"], 2),
            )
            for mes, datos in sorted(por_mes.items())
        ]

        por_cliente = defaultdict(lambda: {"total": 0.0, "cantidad": 0})
        for factura in facturas_anio:
            nombre = factura.client.nombre_razon_social
            por_cliente[nombre]["total"] += float(factura.total)
            por_cliente[nombre]["cantidad"] += 1

        top_clientes = [
            TopCliente(cliente_nombre=nombre, total_comprado=round(datos["total"], 2), cantidad_facturas=datos["cantidad"])
            for nombre, datos in sorted(por_cliente.items(), key=lambda kv: kv[1]["total"], reverse=True)[:5]
        ]

        return DashboardResponse(
            total_facturado_mes_actual=total_facturado_mes,
            igv_recaudado_mes_actual=igv_mes,
            total_morosidad=total_morosidad,
            cantidad_facturas_pendientes=len(facturas_pendientes),
            facturacion_mensual=facturacion_mensual,
            top_clientes=top_clientes,
        )

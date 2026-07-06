from typing import List

from pydantic import BaseModel


class FacturacionMensual(BaseModel):
    mes: str
    total_facturado: float
    igv_recaudado: float


class TopCliente(BaseModel):
    cliente_nombre: str
    total_comprado: float
    cantidad_facturas: int


class DashboardResponse(BaseModel):
    total_facturado_mes_actual: float
    igv_recaudado_mes_actual: float
    total_morosidad: float
    cantidad_facturas_pendientes: int
    facturacion_mensual: List[FacturacionMensual]
    top_clientes: List[TopCliente]

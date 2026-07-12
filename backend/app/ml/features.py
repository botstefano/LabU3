
from dataclasses import dataclass
from datetime import datetime, date
from typing import List, Optional, Dict, Any
from app.models.invoice import Invoice, EstadoFactura
from app.models.payment import Payment
from app.models.client import Client


FEATURE_NAMES = [
    "pct_facturas_vencidas",
    "pct_pagos_tardios",
    "dias_mora_promedio",
    "monto_promedio_factura",
    "cantidad_facturas",
    "antiguedad_dias"
]


@dataclass
class ClientFeatures:
    pct_facturas_vencidas: float
    pct_pagos_tardios: float
    dias_mora_promedio: float
    monto_promedio_factura: float
    cantidad_facturas: int
    antiguedad_dias: int
    label: Optional[int] = None


def compute_client_features(
    client: Client,
    invoices: List[Invoice],
    payments_by_invoice: Dict[str, List[Payment]]
) -> Optional[ClientFeatures]:
    today = date.today()

    resolved_invoices = [
        inv for inv in invoices
        if inv.estado in (EstadoFactura.PAGADA, EstadoFactura.VENCIDA)
    ]

    if not resolved_invoices:
        return None

    total_resolved = len(resolved_invoices)

    vencidas = [inv for inv in resolved_invoices if inv.estado == EstadoFactura.VENCIDA]
    pct_facturas_vencidas = len(vencidas) / total_resolved

    pagadas = [inv for inv in resolved_invoices if inv.estado == EstadoFactura.PAGADA]
    pagos_tardios = 0
    total_mora_days = 0

    for inv in resolved_invoices:
        if inv.estado == EstadoFactura.VENCIDA:
            mora_days = max(0, (today - inv.fecha_vencimiento).days)
            total_mora_days += mora_days
        else:
            inv_payments = payments_by_invoice.get(str(inv.id), [])
            if inv_payments:
                last_payment = max(inv_payments, key=lambda p: p.fecha_pago)
                if last_payment.fecha_pago > inv.fecha_vencimiento:
                    pagos_tardios += 1
                    mora_days = (last_payment.fecha_pago - inv.fecha_vencimiento).days
                    total_mora_days += mora_days

    pct_pagos_tardios = (pagos_tardios / len(pagadas)) if pagadas else 0.0
    dias_mora_promedio = total_mora_days / total_resolved if total_resolved else 0.0

    monto_total = sum(float(inv.total) for inv in resolved_invoices)
    monto_promedio_factura = monto_total / total_resolved if total_resolved else 0.0

    client_created_at = client.created_at.date() if client.created_at else today
    antiguedad_dias = max(1, (today - client_created_at).days)

    label = 1 if (pct_facturas_vencidas > 0.34 or pct_pagos_tardios > 0.34) else 0

    return ClientFeatures(
        pct_facturas_vencidas=pct_facturas_vencidas,
        pct_pagos_tardios=pct_pagos_tardios,
        dias_mora_promedio=dias_mora_promedio,
        monto_promedio_factura=monto_promedio_factura,
        cantidad_facturas=total_resolved,
        antiguedad_dias=antiguedad_dias,
        label=label
    )


def features_to_vector(features: ClientFeatures) -> List[float]:
    return [
        features.pct_facturas_vencidas,
        features.pct_pagos_tardios,
        features.dias_mora_promedio,
        features.monto_promedio_factura,
        features.cantidad_facturas,
        features.antiguedad_dias
    ]


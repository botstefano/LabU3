
import uuid
from typing import List, Dict
from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.models.client import Client
from app.models.invoice import Invoice
from app.models.payment import Payment
from app.repositories.client_repository import ClientRepository
from app.repositories.invoice_repository import InvoiceRepository
from app.repositories.payment_repository import PaymentRepository
from app.services.invoice_service import InvoiceService
from app.schemas.risk import ClientRiskResponse, RiskFactors, TrainRiskResponse
from app.ml.features import compute_client_features, ClientFeatures
from app.ml.risk_model import train_model, predict_proba, model_disponible, TrainResult


def heuristic_score(features: ClientFeatures) -> float:
    score = (
        0.5 * features.pct_facturas_vencidas
        + 0.3 * features.pct_pagos_tardios
        + 0.2 * min(features.dias_mora_promedio / 60, 1.0)
    )
    return max(0.0, min(1.0, score))


def nivel_desde_score(score: float) -> str:
    if score < 0.33:
        return "bajo"
    elif score < 0.66:
        return "medio"
    else:
        return "alto"


class RiskService:
    def __init__(self, db: Session):
        self.db = db
        self.client_repo = ClientRepository(db)
        self.invoice_repo = InvoiceRepository(db)
        self.payment_repo = PaymentRepository(db)
        self.invoice_service = InvoiceService(db)

    def train(self) -> TrainRiskResponse:
        self.invoice_service.actualizar_estados_vencidos()

        clients = self.client_repo.list_all()
        dataset: List[ClientFeatures] = []

        for client in clients:
            invoices = self.invoice_repo.list_all_by_client(client.id)
            payments_by_invoice: Dict[str, List[Payment]] = {}
            for inv in invoices:
                payments = self.payment_repo.list_by_invoice(inv.id)
                payments_by_invoice[str(inv.id)] = payments

            features = compute_client_features(client, invoices, payments_by_invoice)
            if features:
                dataset.append(features)

        result = train_model(dataset)

        return TrainRiskResponse(
            entrenado=result.entrenado,
            n_muestras=result.n_muestras,
            n_clase_alto_riesgo=result.n_clase_alto_riesgo,
            accuracy=result.accuracy,
            f1=result.f1,
            mensaje=result.mensaje,
            modelo_disponible=result.modelo_disponible
        )

    def score_all_clients(self) -> List[ClientRiskResponse]:
        self.invoice_service.actualizar_estados_vencidos()

        clients = self.client_repo.list_all()
        responses: List[ClientRiskResponse] = []

        for client in clients:
            response = self.score_client(client.id, client=client)
            responses.append(response)

        responses.sort(key=lambda r: r.score, reverse=True)
        return responses

    def score_client(self, client_id: uuid.UUID, client: Client = None) -> ClientRiskResponse:
        if not client:
            client = self.client_repo.get_by_id(client_id)
            if not client:
                raise NotFoundError("Cliente no encontrado")

        invoices = self.invoice_repo.list_all_by_client(client.id)
        payments_by_invoice: Dict[str, List[Payment]] = {}
        for inv in invoices:
            payments = self.payment_repo.list_by_invoice(inv.id)
            payments_by_invoice[str(inv.id)] = payments

        features = compute_client_features(client, invoices, payments_by_invoice)

        if not features:
            return ClientRiskResponse(
                client_id=client.id,
                cliente_nombre=client.nombre_razon_social,
                score=0.15,
                nivel="bajo",
                metodo="sin_historial",
                factores=None
            )

        ml_score = predict_proba(features)
        if ml_score is not None:
            score = ml_score
            metodo = "modelo"
        else:
            score = heuristic_score(features)
            metodo = "heuristica"

        return ClientRiskResponse(
            client_id=client.id,
            cliente_nombre=client.nombre_razon_social,
            score=score,
            nivel=nivel_desde_score(score),
            metodo=metodo,
            factores=RiskFactors(
                pct_facturas_vencidas=features.pct_facturas_vencidas,
                pct_pagos_tardios=features.pct_pagos_tardios,
                dias_mora_promedio=features.dias_mora_promedio,
                monto_promedio_factura=features.monto_promedio_factura,
                cantidad_facturas=features.cantidad_facturas,
                antiguedad_dias=features.antiguedad_dias
            )
        )


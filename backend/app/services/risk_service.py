
import uuid
import json
import io
from typing import List, Dict, Optional
from datetime import date, timedelta
from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.models.client import Client
from app.models.invoice import Invoice
from app.models.payment import Payment
from app.repositories.client_repository import ClientRepository
from app.repositories.invoice_repository import InvoiceRepository
from app.repositories.payment_repository import PaymentRepository
from app.services.invoice_service import InvoiceService
from app.schemas.risk import ClientRiskResponse, RiskFactors, TrainRiskResponse, EDAMetrics, TrainingMetrics, TrainingStatus
from app.ml.features import compute_client_features, ClientFeatures, features_to_vector, FEATURE_NAMES
from app.ml.risk_model import train_model, predict_proba, model_disponible, TrainResult, EDAResult, MetricsResult


# Global training state (in-memory, for production use Redis or similar)
_training_state = {
    "status": "idle",  # idle, training, completed, error
    "progress": 0.0,
    "current_step": "",
    "mensaje": "",
    "result": None
}


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

    def _update_training_state(self, status: str, progress: float, current_step: str, mensaje: str, result: Optional[TrainRiskResponse] = None):
        global _training_state
        _training_state["status"] = status
        _training_state["progress"] = progress
        _training_state["current_step"] = current_step
        _training_state["mensaje"] = mensaje
        _training_state["result"] = result

    def get_training_status(self) -> TrainingStatus:
        global _training_state
        return TrainingStatus(
            status=_training_state["status"],
            progress=_training_state["progress"],
            current_step=_training_state["current_step"],
            mensaje=_training_state["mensaje"],
            result=_training_state["result"]
        )

    def parse_dataset_from_csv(self, csv_content: str) -> List[ClientFeatures]:
        """Parse CSV dataset and return list of ClientFeatures"""
        import csv
        
        reader = csv.DictReader(io.StringIO(csv_content))
        dataset = []
        
        for row in reader:
            try:
                features = ClientFeatures(
                    pct_facturas_vencidas=float(row.get('pct_facturas_vencidas', 0)),
                    pct_pagos_tardios=float(row.get('pct_pagos_tardios', 0)),
                    dias_mora_promedio=float(row.get('dias_mora_promedio', 0)),
                    monto_promedio_factura=float(row.get('monto_promedio_factura', 0)),
                    cantidad_facturas=int(row.get('cantidad_facturas', 1)),
                    antiguedad_dias=int(row.get('antiguedad_dias', 1)),
                    label=int(row.get('label', 0)) if row.get('label') else None
                )
                dataset.append(features)
            except (ValueError, KeyError) as e:
                continue  # Skip invalid rows
        
        return dataset

    def parse_dataset_from_json(self, json_content: str) -> List[ClientFeatures]:
        """Parse JSON dataset and return list of ClientFeatures"""
        data = json.loads(json_content)
        dataset = []
        
        if isinstance(data, list):
            for row in data:
                try:
                    features = ClientFeatures(
                        pct_facturas_vencidas=float(row.get('pct_facturas_vencidas', 0)),
                        pct_pagos_tardios=float(row.get('pct_pagos_tardios', 0)),
                        dias_mora_promedio=float(row.get('dias_mora_promedio', 0)),
                        monto_promedio_factura=float(row.get('monto_promedio_factura', 0)),
                        cantidad_facturas=int(row.get('cantidad_facturas', 1)),
                        antiguedad_dias=int(row.get('antiguedad_dias', 1)),
                        label=int(row.get('label', 0)) if row.get('label') is not None else None
                    )
                    dataset.append(features)
                except (ValueError, KeyError) as e:
                    continue
        
        return dataset

    def train_with_dataset(self, dataset: List[ClientFeatures]) -> TrainRiskResponse:
        """Train model with provided dataset (from uploaded file)"""
        self._update_training_state("training", 0.1, "Validando dataset", f"Dataset con {len(dataset)} muestras")
        
        result = train_model(dataset)
        
        # Convert result to response schema
        eda_response = None
        if result.eda:
            eda_response = EDAMetrics(
                n_muestras=result.eda.n_muestras,
                n_clase_alto_riesgo=result.eda.n_clase_alto_riesgo,
                n_clase_bajo_riesgo=result.eda.n_clase_bajo_riesgo,
                feature_stats=result.eda.feature_stats,
                class_balance=result.eda.class_balance
            )
        
        metrics_response = None
        if result.metrics:
            metrics_response = TrainingMetrics(
                accuracy=result.metrics.accuracy,
                precision=result.metrics.precision,
                recall=result.metrics.recall,
                f1=result.metrics.f1,
                confusion_matrix=result.metrics.confusion_matrix,
                feature_importance=result.metrics.feature_importance
            )
        
        response = TrainRiskResponse(
            entrenado=result.entrenado,
            n_muestras=result.n_muestras,
            n_clase_alto_riesgo=result.n_clase_alto_riesgo,
            accuracy=result.accuracy,
            f1=result.f1,
            mensaje=result.mensaje,
            modelo_disponible=result.modelo_disponible,
            eda=eda_response,
            metrics=metrics_response
        )
        
        status = "completed" if result.entrenado else "error"
        self._update_training_state(status, 1.0, "Completado", result.mensaje, response)
        
        return response

    def train(self) -> TrainRiskResponse:
        """Train model with data from database"""
        self._update_training_state("training", 0.1, "Actualizando estados de facturas", "")
        self.invoice_service.actualizar_estados_vencidos()

        self._update_training_state("training", 0.3, "Cargando clientes", "")
        clients = self.client_repo.list_all()
        dataset: List[ClientFeatures] = []

        self._update_training_state("training", 0.5, "Calculando features", f"Procesando {len(clients)} clientes")
        for i, client in enumerate(clients):
            invoices = self.invoice_repo.list_all_by_client(client.id)
            payments_by_invoice: Dict[str, List[Payment]] = {}
            for inv in invoices:
                payments = self.payment_repo.list_by_invoice(inv.id)
                payments_by_invoice[str(inv.id)] = payments

            features = compute_client_features(client, invoices, payments_by_invoice)
            if features:
                dataset.append(features)
            
            # Update progress
            progress = 0.5 + (0.3 * (i + 1) / len(clients))
            self._update_training_state("training", progress, "Calculando features", f"{i + 1}/{len(clients)} clientes procesados")

        self._update_training_state("training", 0.8, "Entrenando modelo", "")
        result = train_model(dataset)

        # Convert result to response schema
        eda_response = None
        if result.eda:
            eda_response = EDAMetrics(
                n_muestras=result.eda.n_muestras,
                n_clase_alto_riesgo=result.eda.n_clase_alto_riesgo,
                n_clase_bajo_riesgo=result.eda.n_clase_bajo_riesgo,
                feature_stats=result.eda.feature_stats,
                class_balance=result.eda.class_balance
            )
        
        metrics_response = None
        if result.metrics:
            metrics_response = TrainingMetrics(
                accuracy=result.metrics.accuracy,
                precision=result.metrics.precision,
                recall=result.metrics.recall,
                f1=result.metrics.f1,
                confusion_matrix=result.metrics.confusion_matrix,
                feature_importance=result.metrics.feature_importance
            )

        response = TrainRiskResponse(
            entrenado=result.entrenado,
            n_muestras=result.n_muestras,
            n_clase_alto_riesgo=result.n_clase_alto_riesgo,
            accuracy=result.accuracy,
            f1=result.f1,
            mensaje=result.mensaje,
            modelo_disponible=result.modelo_disponible,
            eda=eda_response,
            metrics=metrics_response
        )
        
        status = "completed" if result.entrenado else "error"
        self._update_training_state(status, 1.0, "Completado", result.mensaje, response)

        return response

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


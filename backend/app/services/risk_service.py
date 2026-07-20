
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
from app.schemas.risk import ClientRiskResponse, RiskFactors, TrainRiskResponse, EDAMetrics, TrainingMetrics, TrainingStatus, CompareModelsResponse
from app.ml.features import compute_client_features, ClientFeatures, features_to_vector, FEATURE_NAMES
from app.ml.risk_model import train_model, predict_proba, model_disponible, TrainResult, EDAResult, MetricsResult, compare_models, train_model_with_type


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
            nivel_ml = nivel_desde_score(ml_score)
        else:
            score = heuristic_score(features)
            metodo = "heuristica"
            nivel_ml = None

        # Always calculate heuristic level for comparison
        heuristic_score_value = heuristic_score(features)
        nivel_heuristico = nivel_desde_score(heuristic_score_value)

        return ClientRiskResponse(
            client_id=client.id,
            cliente_nombre=client.nombre_razon_social,
            score=score,
            nivel=nivel_desde_score(score),
            metodo=metodo,
            nivel_heuristico=nivel_heuristico,
            nivel_ml=nivel_ml,
            factores=RiskFactors(
                pct_facturas_vencidas=features.pct_facturas_vencidas,
                pct_pagos_tardios=features.pct_pagos_tardios,
                dias_mora_promedio=features.dias_mora_promedio,
                monto_promedio_factura=features.monto_promedio_factura,
                cantidad_facturas=features.cantidad_facturas,
                antiguedad_dias=features.antiguedad_dias
            )
        )

    def compare_models(self) -> CompareModelsResponse:
        """Compare multiple models using cross-validation and statistical analysis"""
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

        if not dataset:
            return CompareModelsResponse(
                results=[],
                best_model="",
                best_f1=0.0,
                recommendation="No hay suficientes clientes con historial para comparar modelos.",
                statistical_tests={}
            )

        result = compare_models(dataset)
        
        return CompareModelsResponse(
            results=result.results,
            best_model=result.best_model,
            best_f1=result.best_f1,
            recommendation=result.recommendation,
            statistical_tests=result.statistical_tests
        )

    def train_with_type(self, model_type: str) -> TrainRiskResponse:
        """Train a specific model type and persist it"""
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

        result = train_model_with_type(dataset, model_type)

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

        return TrainRiskResponse(
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

    def listar_clientes_para_cobranza(self) -> list:
        """Listar clientes priorizados por riesgo de morosidad para cobranza"""
        self.invoice_service.actualizar_estados_vencidos()

        clients = self.client_repo.list_all()
        clientes_con_riesgo = []

        for client in clients:
            try:
                riesgo = self.score_client(client.id)
                clientes_con_riesgo.append({
                    "client_id": str(client.id),
                    "cliente_nombre": client.nombre_razon_social,
                    "score": riesgo.score,
                    "nivel": riesgo.nivel,
                    "metodo": riesgo.metodo,
                    "pct_facturas_vencidas": riesgo.factores.pct_facturas_vencidas if riesgo.factores else 0,
                    "pct_pagos_tardios": riesgo.factores.pct_pagos_tardios if riesgo.factores else 0,
                    "dias_mora_promedio": riesgo.factores.dias_mora_promedio if riesgo.factores else 0,
                })
            except Exception:
                # Si no se puede calcular riesgo, continuar
                pass

        # Ordenar por riesgo (mayor primero)
        clientes_priorizados = sorted(clientes_con_riesgo, key=lambda x: x["score"], reverse=True)
        return clientes_priorizados

    def sugerir_limite_credito(self, client_id: str) -> dict:
        """Sugerir límite de crédito basado en riesgo del cliente"""
        try:
            riesgo = self.score_client(client_id)
            
            # Use heuristic level for credit limits (more conservative, based on actual behavior)
            nivel_para_limite = riesgo.nivel_heuristico if riesgo.nivel_heuristico else riesgo.nivel
            
            if nivel_para_limite == "bajo":
                limite = 10000  # S/ 10,000
                justificacion = "Cliente con bajo riesgo de morosidad. Límite de crédito alto."
            elif nivel_para_limite == "medio":
                limite = 5000  # S/ 5,000
                justificacion = "Cliente con riesgo medio de morosidad. Límite de crédito moderado."
            else:  # alto
                limite = 1000  # S/ 1,000
                justificacion = "Cliente con alto riesgo de morosidad. Límite de crédito bajo."
            
            return {
                "client_id": client_id,
                "limite_sugerido": limite,
                "nivel_riesgo": nivel_para_limite,
                "score_riesgo": riesgo.score,
                "justificacion": justificacion,
                "factores": {
                    "pct_facturas_vencidas": riesgo.factores.pct_facturas_vencidas if riesgo.factores else 0,
                    "pct_pagos_tardios": riesgo.factores.pct_pagos_tardios if riesgo.factores else 0,
                    "dias_mora_promedio": riesgo.factores.dias_mora_promedio if riesgo.factores else 0,
                }
            }
        except Exception as e:
            # Si no se puede calcular riesgo, retornar límite conservador
            return {
                "client_id": client_id,
                "limite_sugerido": 1000,
                "nivel_riesgo": "desconocido",
                "score_riesgo": 0.0,
                "justificacion": "No se pudo calcular el riesgo. Límite conservador.",
                "factores": {
                    "pct_facturas_vencidas": 0,
                    "pct_pagos_tardios": 0,
                    "dias_mora_promedio": 0,
                }
            }


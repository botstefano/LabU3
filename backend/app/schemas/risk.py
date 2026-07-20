
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from uuid import UUID


class RiskFactors(BaseModel):
    pct_facturas_vencidas: float
    pct_pagos_tardios: float
    dias_mora_promedio: float
    monto_promedio_factura: float
    cantidad_facturas: int
    antiguedad_dias: int


class ClientRiskResponse(BaseModel):
    client_id: UUID
    cliente_nombre: str
    score: float
    nivel: str
    metodo: str
    nivel_heuristico: Optional[str] = None  # Nivel calculado por heurística
    nivel_ml: Optional[str] = None  # Nivel calculado por modelo ML
    factores: Optional[RiskFactors] = None


class EDAMetrics(BaseModel):
    n_muestras: int
    n_clase_alto_riesgo: int
    n_clase_bajo_riesgo: int
    feature_stats: Dict[str, Dict[str, float]]
    class_balance: Dict[str, int]


class TrainingMetrics(BaseModel):
    accuracy: float
    precision: float
    recall: float
    f1: float
    confusion_matrix: List[List[int]]
    feature_importance: Dict[str, float]


class TrainRiskResponse(BaseModel):
    entrenado: bool
    n_muestras: int
    n_clase_alto_riesgo: int
    accuracy: Optional[float] = None
    f1: Optional[float] = None
    mensaje: str
    modelo_disponible: bool
    eda: Optional[EDAMetrics] = None
    metrics: Optional[TrainingMetrics] = None


class TrainingStatus(BaseModel):
    status: str  # "idle", "training", "completed", "error"
    progress: float  # 0.0 to 1.0
    current_step: str
    mensaje: str
    result: Optional[TrainRiskResponse] = None


class ModelComparisonResult(BaseModel):
    model_config = {'protected_namespaces': ()}
    model_name: str
    f1_mean: float
    f1_std: float
    f1_scores: List[float]
    accuracy_mean: float
    accuracy_std: float
    precision_mean: float
    precision_std: float
    recall_mean: float
    recall_std: float
    roc_auc_mean: float
    roc_auc_std: float
    training_time: float
    feature_importance: Dict[str, float]


class CompareModelsResponse(BaseModel):
    results: List[ModelComparisonResult]
    best_model: str
    best_f1: float
    recommendation: str
    statistical_tests: Dict[str, Any]
    correlation_matrix: Optional[Dict[str, Dict[str, float]]] = None
    roc_curves: Optional[Dict[str, Dict[str, List[float]]]] = None


class TrainModelWithTypeRequest(BaseModel):
    model_config = {'protected_namespaces': ()}
    model_type: str  # "logistic", "random_forest", "svm", "gradient_boosting", "mlp"


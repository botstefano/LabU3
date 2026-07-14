
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


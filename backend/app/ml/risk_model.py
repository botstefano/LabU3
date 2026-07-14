
import os
from pathlib import Path
from typing import List, Optional, Tuple, Dict, Any
from dataclasses import dataclass

import joblib
import numpy as np
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score, confusion_matrix

from app.ml.features import ClientFeatures, features_to_vector, FEATURE_NAMES


MODEL_PATH = Path(__file__).parent / "model_artifacts" / "risk_model.joblib"


@dataclass
class EDAResult:
    n_muestras: int
    n_clase_alto_riesgo: int
    n_clase_bajo_riesgo: int
    feature_stats: Dict[str, Dict[str, float]]
    class_balance: Dict[str, int]


@dataclass
class MetricsResult:
    accuracy: float
    precision: float
    recall: float
    f1: float
    confusion_matrix: List[List[int]]
    feature_importance: Dict[str, float]


@dataclass
class TrainResult:
    entrenado: bool
    mensaje: str
    n_muestras: int
    n_clase_alto_riesgo: int
    accuracy: Optional[float] = None
    f1: Optional[float] = None
    modelo_disponible: bool = False
    eda: Optional[EDAResult] = None
    metrics: Optional[MetricsResult] = None


def _build_pipeline() -> Pipeline:
    return Pipeline([
        ("scaler", StandardScaler()),
        ("classifier", LogisticRegression(class_weight="balanced", random_state=42))
    ])


def _compute_eda(dataset: List[ClientFeatures]) -> EDAResult:
    X = np.array([features_to_vector(f) for f in dataset])
    labels = np.array([f.label for f in dataset])
    
    n_muestras = len(dataset)
    n_clase_alto_riesgo = sum(1 for l in labels if l == 1)
    n_clase_bajo_riesgo = sum(1 for l in labels if l == 0)
    
    feature_stats = {}
    for i, name in enumerate(FEATURE_NAMES):
        col = X[:, i]
        feature_stats[name] = {
            "mean": float(np.mean(col)),
            "std": float(np.std(col)),
            "min": float(np.min(col)),
            "max": float(np.max(col)),
            "median": float(np.median(col))
        }
    
    class_balance = {
        "alto_riesgo": n_clase_alto_riesgo,
        "bajo_riesgo": n_clase_bajo_riesgo
    }
    
    return EDAResult(
        n_muestras=n_muestras,
        n_clase_alto_riesgo=n_clase_alto_riesgo,
        n_clase_bajo_riesgo=n_clase_bajo_riesgo,
        feature_stats=feature_stats,
        class_balance=class_balance
    )


def _compute_metrics(pipeline: Pipeline, X_test: np.ndarray, y_test: np.ndarray) -> MetricsResult:
    y_pred = pipeline.predict(X_test)
    
    accuracy = float(accuracy_score(y_test, y_pred))
    precision = float(precision_score(y_test, y_pred, zero_division=0))
    recall = float(recall_score(y_test, y_pred, zero_division=0))
    f1 = float(f1_score(y_test, y_pred, zero_division=0))
    
    cm = confusion_matrix(y_test, y_pred)
    confusion_matrix_list = cm.tolist()
    
    # Feature importance from logistic regression coefficients
    classifier = pipeline.named_steps['classifier']
    scaler = pipeline.named_steps['scaler']
    
    # Get coefficients and scale them by feature std for interpretability
    coef = classifier.coef_[0]
    feature_std = scaler.scale_
    feature_importance = {}
    for i, name in enumerate(FEATURE_NAMES):
        importance = abs(coef[i] * feature_std[i])
        feature_importance[name] = float(importance)
    
    # Normalize to percentage
    total = sum(feature_importance.values())
    if total > 0:
        feature_importance = {k: (v / total) * 100 for k, v in feature_importance.items()}
    
    return MetricsResult(
        accuracy=accuracy,
        precision=precision,
        recall=recall,
        f1=f1,
        confusion_matrix=confusion_matrix_list,
        feature_importance=feature_importance
    )


def train_model(dataset: List[ClientFeatures]) -> TrainResult:
    n_muestras = len(dataset)
    labels = [f.label for f in dataset if f.label is not None]
    n_clase_alto_riesgo = sum(1 for l in labels if l == 1)
    n_clase_bajo_riesgo = sum(1 for l in labels if l == 0)

    if n_muestras < 12 or n_clase_alto_riesgo == 0 or n_clase_bajo_riesgo == 0:
        return TrainResult(
            entrenado=False,
            mensaje=f"No hay suficientes datos: {n_muestras} muestras, {n_clase_alto_riesgo} alto riesgo, {n_clase_bajo_riesgo} bajo riesgo. Se necesitan al menos ~12 muestras y ambas clases presentes.",
            n_muestras=n_muestras,
            n_clase_alto_riesgo=n_clase_alto_riesgo,
            modelo_disponible=model_disponible()
        )

    # Compute EDA
    eda = _compute_eda(dataset)

    X = np.array([features_to_vector(f) for f in dataset])
    y = np.array([f.label for f in dataset])

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    pipeline = _build_pipeline()
    pipeline.fit(X_train, y_train)

    # Compute detailed metrics
    metrics = _compute_metrics(pipeline, X_test, y_test)

    pipeline_final = _build_pipeline()
    pipeline_final.fit(X, y)

    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(pipeline_final, MODEL_PATH)

    return TrainResult(
        entrenado=True,
        mensaje="Modelo entrenado exitosamente!",
        n_muestras=n_muestras,
        n_clase_alto_riesgo=n_clase_alto_riesgo,
        accuracy=metrics.accuracy,
        f1=metrics.f1,
        modelo_disponible=True,
        eda=eda,
        metrics=metrics
    )


def predict_proba(features: ClientFeatures) -> Optional[float]:
    if not model_disponible():
        return None

    pipeline = joblib.load(MODEL_PATH)
    X = np.array([features_to_vector(features)])
    proba = pipeline.predict_proba(X)[0]

    return float(proba[1])


def model_disponible() -> bool:
    return MODEL_PATH.exists()



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
from sklearn.metrics import accuracy_score, f1_score

from app.ml.features import ClientFeatures, features_to_vector, FEATURE_NAMES


MODEL_PATH = Path(__file__).parent / "model_artifacts" / "risk_model.joblib"


@dataclass
class TrainResult:
    entrenado: bool
    mensaje: str
    n_muestras: int
    n_clase_alto_riesgo: int
    accuracy: Optional[float] = None
    f1: Optional[float] = None
    modelo_disponible: bool = False


def _build_pipeline() -> Pipeline:
    return Pipeline([
        ("scaler", StandardScaler()),
        ("classifier", LogisticRegression(class_weight="balanced", random_state=42))
    ])


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

    X = np.array([features_to_vector(f) for f in dataset])
    y = np.array([f.label for f in dataset])

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    pipeline = _build_pipeline()
    pipeline.fit(X_train, y_train)

    y_pred = pipeline.predict(X_test)
    accuracy = float(accuracy_score(y_test, y_pred))
    f1 = float(f1_score(y_test, y_pred, zero_division=0))

    pipeline_final = _build_pipeline()
    pipeline_final.fit(X, y)

    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(pipeline_final, MODEL_PATH)

    return TrainResult(
        entrenado=True,
        mensaje="Modelo entrenado exitosamente!",
        n_muestras=n_muestras,
        n_clase_alto_riesgo=n_clase_alto_riesgo,
        accuracy=accuracy,
        f1=f1,
        modelo_disponible=True
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


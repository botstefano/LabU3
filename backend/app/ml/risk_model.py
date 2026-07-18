
import os
from pathlib import Path
from typing import List, Optional, Tuple, Dict, Any, Literal
from dataclasses import dataclass
import time
import json

import joblib
import numpy as np
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.svm import SVC
from sklearn.neural_network import MLPClassifier
from sklearn.model_selection import train_test_split, cross_val_score, StratifiedKFold
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score, confusion_matrix, roc_auc_score, roc_curve
from scipy import stats

from app.ml.features import ClientFeatures, features_to_vector, FEATURE_NAMES


MODEL_PATH = Path(__file__).parent / "model_artifacts" / "risk_model.joblib"
DATASET_PATH = Path(__file__).parent / "model_artifacts" / "training_dataset.json"


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


@dataclass
class ModelComparisonResult:
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


@dataclass
class CompareModelsResult:
    results: List[ModelComparisonResult]
    best_model: str
    best_f1: float
    recommendation: str
    statistical_tests: Dict[str, Any]
    correlation_matrix: Optional[Dict[str, Dict[str, float]]] = None
    roc_curves: Optional[Dict[str, Dict[str, List[float]]]] = None


def _build_pipeline(model_type: Literal["logistic", "random_forest", "svm", "gradient_boosting", "mlp"]) -> Pipeline:
    """Build pipeline for different model types"""
    if model_type == "logistic":
        return Pipeline([
            ("scaler", StandardScaler()),
            ("classifier", LogisticRegression(class_weight="balanced", random_state=42, max_iter=1000))
        ])
    elif model_type == "random_forest":
        return Pipeline([
            ("classifier", RandomForestClassifier(
                n_estimators=100,
                class_weight="balanced",
                random_state=42,
                n_jobs=-1
            ))
        ])
    elif model_type == "svm":
        return Pipeline([
            ("scaler", StandardScaler()),
            ("classifier", SVC(
                class_weight="balanced",
                probability=True,
                random_state=42
            ))
        ])
    elif model_type == "gradient_boosting":
        return Pipeline([
            ("classifier", GradientBoostingClassifier(
                n_estimators=100,
                random_state=42
            ))
        ])
    elif model_type == "mlp":
        return Pipeline([
            ("scaler", StandardScaler()),
            ("classifier", MLPClassifier(
                hidden_layer_sizes=(64, 32),
                max_iter=1000,
                random_state=42,
                early_stopping=True
            ))
        ])
    else:
        raise ValueError(f"Unknown model type: {model_type}")


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


def _compute_feature_importance(pipeline: Pipeline, model_type: str) -> Dict[str, float]:
    """Compute feature importance based on model type"""
    feature_importance = {}
    
    if model_type == "logistic":
        classifier = pipeline.named_steps['classifier']
        scaler = pipeline.named_steps['scaler']
        coef = classifier.coef_[0]
        feature_std = scaler.scale_
        for i, name in enumerate(FEATURE_NAMES):
            importance = abs(coef[i] * feature_std[i])
            feature_importance[name] = float(importance)
    elif model_type == "random_forest":
        classifier = pipeline.named_steps['classifier']
        for i, name in enumerate(FEATURE_NAMES):
            feature_importance[name] = float(classifier.feature_importances_[i])
    elif model_type == "gradient_boosting":
        classifier = pipeline.named_steps['classifier']
        for i, name in enumerate(FEATURE_NAMES):
            feature_importance[name] = float(classifier.feature_importances_[i])
    elif model_type == "svm":
        # SVM doesn't have direct feature importance, use permutation importance approximation
        # For simplicity, return equal weights
        for name in FEATURE_NAMES:
            feature_importance[name] = 1.0 / len(FEATURE_NAMES)
    elif model_type == "mlp":
        # MLP doesn't have direct feature importance, use equal weights
        for name in FEATURE_NAMES:
            feature_importance[name] = 1.0 / len(FEATURE_NAMES)
    
    # Normalize to percentage
    total = sum(feature_importance.values())
    if total > 0:
        feature_importance = {k: (v / total) * 100 for k, v in feature_importance.items()}
    
    return feature_importance


def _compute_correlation_matrix(X: np.ndarray) -> Dict[str, Dict[str, float]]:
    """Compute correlation matrix for features"""
    import pandas as pd
    
    df = pd.DataFrame(X, columns=FEATURE_NAMES)
    corr_matrix = df.corr()
    
    # Convert to nested dict
    corr_dict = {}
    for i, name_i in enumerate(FEATURE_NAMES):
        corr_dict[name_i] = {}
        for j, name_j in enumerate(FEATURE_NAMES):
            corr_dict[name_i][name_j] = float(corr_matrix.iloc[i, j])
    
    return corr_dict


def _compute_roc_curves(X: np.ndarray, y: np.ndarray, models_config: Dict[str, str]) -> Dict[str, Dict[str, List[float]]]:
    """Compute ROC curves for all models"""
    from sklearn.model_selection import train_test_split
    
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.3, random_state=42, stratify=y
    )
    
    roc_curves = {}
    
    for model_type, model_name in models_config.items():
        try:
            pipeline = _build_pipeline(model_type)
            pipeline.fit(X_train, y_train)
            
            # Get probabilities
            if hasattr(pipeline, 'predict_proba'):
                y_proba = pipeline.predict_proba(X_test)[:, 1]
            else:
                # Fallback for models without predict_proba
                y_proba = pipeline.decision_function(X_test)
                # Normalize to 0-1
                y_proba = (y_proba - y_proba.min()) / (y_proba.max() - y_proba.min() + 1e-10)
            
            # Compute ROC curve
            fpr, tpr, _ = roc_curve(y_test, y_proba)
            
            roc_curves[model_name] = {
                "fpr": fpr.tolist(),
                "tpr": tpr.tolist(),
                "auc": float(roc_auc_score(y_test, y_proba))
            }
        except Exception as e:
            # Skip models that fail ROC computation
            print(f"Warning: Could not compute ROC curve for {model_name}: {e}")
    
    return roc_curves


def compare_models(dataset: List[ClientFeatures]) -> CompareModelsResult:
    """Compare multiple models using cross-validation and statistical analysis"""
    n_muestras = len(dataset)
    labels = [f.label for f in dataset if f.label is not None]
    n_clase_alto_riesgo = sum(1 for l in labels if l == 1)
    n_clase_bajo_riesgo = sum(1 for l in labels if l == 0)

    if n_muestras < 12 or n_clase_alto_riesgo == 0 or n_clase_bajo_riesgo == 0:
        return CompareModelsResult(
            results=[],
            best_model="",
            best_f1=0.0,
            recommendation=f"No hay suficientes datos: {n_muestras} muestras, {n_clase_alto_riesgo} alto riesgo, {n_clase_bajo_riesgo} bajo riesgo. Se necesitan al menos ~12 muestras y ambas clases presentes.",
            statistical_tests={}
        )

    X = np.array([features_to_vector(f) for f in dataset])
    y = np.array([f.label for f in dataset])

    # Compute correlation matrix
    correlation_matrix = _compute_correlation_matrix(X)

    # Model configurations
    models_config = {
        "logistic": "Logistic Regression",
        "random_forest": "Random Forest",
        "svm": "Support Vector Machine",
        "gradient_boosting": "Gradient Boosting",
        "mlp": "Neural Network (MLP)"
    }

    # Compute ROC curves
    roc_curves = _compute_roc_curves(X, y, models_config)

    # Adjust n_splits based on dataset size
    min_class_size = min(np.sum(y == 0), np.sum(y == 1))
    n_splits = min(10, min_class_size)
    if n_splits < 2:
        n_splits = 2  # Minimum 2 splits for cross-validation

    # Stratified cross-validation
    cv = StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=42)
    
    results = []
    model_results = {}  # Store results for statistical tests

    for model_type, model_name in models_config.items():
        print(f"Evaluating {model_name}...")
        
        pipeline = _build_pipeline(model_type)
        
        # Measure training time
        start_time = time.time()
        pipeline.fit(X, y)
        training_time = time.time() - start_time
        
        # Cross-validation scores
        f1_scores = cross_val_score(pipeline, X, y, cv=cv, scoring='f1')
        accuracy_scores = cross_val_score(pipeline, X, y, cv=cv, scoring='accuracy')
        precision_scores = cross_val_score(pipeline, X, y, cv=cv, scoring='precision')
        recall_scores = cross_val_score(pipeline, X, y, cv=cv, scoring='recall')
        
        # ROC-AUC (only if model supports probability)
        try:
            roc_auc_scores = cross_val_score(pipeline, X, y, cv=cv, scoring='roc_auc')
        except:
            roc_auc_scores = np.array([0.0])  # Fallback if ROC not supported
        
        # Compute feature importance
        feature_importance = _compute_feature_importance(pipeline, model_type)
        
        result = ModelComparisonResult(
            model_name=model_name,
            f1_mean=float(f1_scores.mean()),
            f1_std=float(f1_scores.std()),
            f1_scores=f1_scores.tolist(),
            accuracy_mean=float(accuracy_scores.mean()),
            accuracy_std=float(accuracy_scores.std()),
            precision_mean=float(precision_scores.mean()),
            precision_std=float(precision_scores.std()),
            recall_mean=float(recall_scores.mean()),
            recall_std=float(recall_scores.std()),
            roc_auc_mean=float(roc_auc_scores.mean()),
            roc_auc_std=float(roc_auc_scores.std()),
            training_time=float(training_time),
            feature_importance=feature_importance
        )
        
        results.append(result)
        model_results[model_type] = {
            'f1_scores': f1_scores,
            'accuracy_scores': accuracy_scores
        }

    # Determine best model based on F1-score
    best_result = max(results, key=lambda r: r.f1_mean)
    best_model = best_result.model_name
    best_f1 = best_result.f1_mean

    # Statistical tests (paired t-test between best and others)
    statistical_tests = {}
    best_f1_scores = None
    for result in results:
        if result.model_name == best_model:
            # Find the model type
            for model_type, name in models_config.items():
                if name == best_model:
                    best_f1_scores = model_results[model_type]['f1_scores']
                    break
            break

    for result in results:
        if result.model_name != best_model:
            # Find the model type
            other_model_type = None
            for model_type, name in models_config.items():
                if name == result.model_name:
                    other_model_type = model_type
                    break
            
            if other_model_type and best_f1_scores is not None:
                other_f1_scores = model_results[other_model_type]['f1_scores']
                t_stat, p_value = stats.ttest_rel(best_f1_scores, other_f1_scores)
                statistical_tests[f"{best_model}_vs_{result.model_name}"] = {
                    "t_statistic": float(t_stat),
                    "p_value": float(p_value),
                    "significant": p_value < 0.05
                }

    # Generate recommendation
    if best_f1 > 0.8:
        recommendation = f"El modelo {best_model} muestra un rendimiento excelente (F1={best_f1:.3f}). Se recomienda su implementación en producción."
    elif best_f1 > 0.7:
        recommendation = f"El modelo {best_model} muestra un rendimiento bueno (F1={best_f1:.3f}). Es adecuado para producción con monitoreo continuo."
    elif best_f1 > 0.6:
        recommendation = f"El modelo {best_model} muestra un rendimiento moderado (F1={best_f1:.3f}). Se recomienda mejorar la calidad de datos o features."
    else:
        recommendation = f"El modelo {best_model} muestra un rendimiento bajo (F1={best_f1:.3f}). Se recomienda recolectar más datos o revisar la ingeniería de features."

    return CompareModelsResult(
        results=results,
        best_model=best_model,
        best_f1=best_f1,
        recommendation=recommendation,
        statistical_tests=statistical_tests,
        correlation_matrix=correlation_matrix,
        roc_curves=roc_curves
    )


def train_model_with_type(dataset: List[ClientFeatures], model_type: str = "logistic") -> TrainResult:
    """Train a specific model type and persist it"""
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

    eda = _compute_eda(dataset)
    X = np.array([features_to_vector(f) for f in dataset])
    y = np.array([f.label for f in dataset])

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    pipeline = _build_pipeline(model_type)
    pipeline.fit(X_train, y_train)

    metrics = _compute_metrics(pipeline, X_test, y_test)

    pipeline_final = _build_pipeline(model_type)
    pipeline_final.fit(X, y)

    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(pipeline_final, MODEL_PATH)

    return TrainResult(
        entrenado=True,
        mensaje=f"Modelo {model_type} entrenado exitosamente!",
        n_muestras=n_muestras,
        n_clase_alto_riesgo=n_clase_alto_riesgo,
        accuracy=metrics.accuracy,
        f1=metrics.f1,
        modelo_disponible=True,
        eda=eda,
        metrics=metrics
    )


def save_training_dataset(dataset: List[ClientFeatures]) -> None:
    """Save training dataset to JSON file for incremental training"""
    DATASET_PATH.parent.mkdir(parents=True, exist_ok=True)
    dataset_dict = [
        {
            "pct_facturas_vencidas": f.pct_facturas_vencidas,
            "pct_pagos_tardios": f.pct_pagos_tardios,
            "dias_mora_promedio": f.dias_mora_promedio,
            "monto_promedio_factura": f.monto_promedio_factura,
            "cantidad_facturas": f.cantidad_facturas,
            "antiguedad_dias": f.antiguedad_dias,
            "label": f.label
        }
        for f in dataset
    ]
    with open(DATASET_PATH, 'w') as f:
        json.dump(dataset_dict, f, indent=2)


def load_training_dataset() -> List[ClientFeatures]:
    """Load saved training dataset from JSON file"""
    if not DATASET_PATH.exists():
        return []
    
    with open(DATASET_PATH, 'r') as f:
        dataset_dict = json.load(f)
    
    return [
        ClientFeatures(
            pct_facturas_vencidas=item["pct_facturas_vencidas"],
            pct_pagos_tardios=item["pct_pagos_tardios"],
            dias_mora_promedio=item["dias_mora_promedio"],
            monto_promedio_factura=item["monto_promedio_factura"],
            cantidad_facturas=item["cantidad_facturas"],
            antiguedad_dias=item["antiguedad_dias"],
            label=item["label"]
        )
        for item in dataset_dict
    ]


def combine_datasets(saved_dataset: List[ClientFeatures], new_dataset: List[ClientFeatures]) -> List[ClientFeatures]:
    """Combine saved dataset with new dataset from database"""
    # Simple concatenation - could add deduplication logic based on client ID if needed
    return saved_dataset + new_dataset


def train_model_with_type_incremental(
    new_dataset: List[ClientFeatures],
    model_type: str = "logistic",
    use_saved: bool = True
) -> TrainResult:
    """Train model incrementally: combine saved dataset with new data"""
    saved_dataset = load_training_dataset() if use_saved else []
    
    if saved_dataset:
        combined_dataset = combine_datasets(saved_dataset, new_dataset)
        print(f"Entrenamiento incremental: {len(saved_dataset)} datos guardados + {len(new_dataset)} nuevos = {len(combined_dataset)} total")
    else:
        combined_dataset = new_dataset
        print(f"Primer entrenamiento: {len(new_dataset)} datos")
    
    # Save the combined dataset for future incremental training
    save_training_dataset(combined_dataset)
    
    # Train with the combined dataset
    return train_model_with_type(combined_dataset, model_type)


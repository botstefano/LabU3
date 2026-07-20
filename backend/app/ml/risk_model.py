
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
from sklearn.model_selection import train_test_split, cross_val_score, cross_val_predict, StratifiedKFold
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score, confusion_matrix, roc_auc_score, roc_curve
from sklearn.model_selection import learning_curve
from sklearn.calibration import calibration_curve
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
    hyperparameters: Optional[Dict[str, Any]] = None
    confusion_matrix: Optional[List[List[int]]] = None


@dataclass
class CompareModelsResult:
    results: List[ModelComparisonResult]
    best_model: str
    best_f1: float
    recommendation: str
    statistical_tests: Dict[str, Any]
    correlation_matrix: Optional[Dict[str, Dict[str, float]]] = None
    roc_curves: Optional[Dict[str, Dict[str, List[float]]]] = None
    out_of_fold_predictions: Optional[Dict[str, np.ndarray]] = None  # model_name -> predictions
    # Additional statistical tests
    wilcoxon_tests: Optional[Dict[str, Any]] = None
    mcnemar_tests: Optional[Dict[str, Any]] = None
    bootstrap_intervals: Optional[Dict[str, Dict[str, Tuple[float, float]]]] = None
    variance_analysis: Optional[Dict[str, Dict[str, float]]] = None
    learning_curves: Optional[Dict[str, Dict[str, List[float]]]] = None
    calibration_curves: Optional[Dict[str, Dict[str, List[float]]]] = None
    feature_importance_stability: Optional[Dict[str, Dict[str, float]]] = None


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
        from sklearn.calibration import CalibratedClassifierCV
        return Pipeline([
            ("scaler", StandardScaler()),
            ("classifier", CalibratedClassifierCV(
                SVC(class_weight="balanced", random_state=42),
                ensemble=False
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
                early_stopping=True,
                validation_fraction=0.1,
                n_iter_no_change=10
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

    # Feature importance from model
    classifier = pipeline.named_steps['classifier']
    feature_importance = {}

    # Handle different model types for feature importance
    if hasattr(classifier, 'coef_'):
        # Linear models (Logistic Regression, SVM)
        scaler = pipeline.named_steps.get('scaler')
        if scaler is not None:
            # Scale coefficients by feature std for interpretability
            coef = classifier.coef_[0]
            feature_std = scaler.scale_
            for i, name in enumerate(FEATURE_NAMES):
                importance = abs(coef[i] * feature_std[i])
                feature_importance[name] = float(importance)
        else:
            # No scaler, use raw coefficients
            coef = classifier.coef_[0]
            for i, name in enumerate(FEATURE_NAMES):
                importance = abs(coef[i])
                feature_importance[name] = float(importance)
    elif hasattr(classifier, 'feature_importances_'):
        # Tree-based models (Random Forest, Gradient Boosting)
        importances = classifier.feature_importances_
        for i, name in enumerate(FEATURE_NAMES):
            feature_importance[name] = float(importances[i])
    elif hasattr(classifier, 'coefs_'):
        # Neural Network (MLP)
        # Use first layer weights as approximation
        coefs = classifier.coefs_[0]
        for i, name in enumerate(FEATURE_NAMES):
            importance = np.mean(np.abs(coefs[i]))
            feature_importance[name] = float(importance)
    else:
        # Fallback: equal importance
        for name in FEATURE_NAMES:
            feature_importance[name] = 100.0 / len(FEATURE_NAMES)

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

    pipeline = _build_pipeline("logistic")
    pipeline.fit(X_train, y_train)

    # Compute detailed metrics
    metrics = _compute_metrics(pipeline, X_test, y_test)

    pipeline_final = _build_pipeline("logistic")
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


def _compute_wilcoxon_tests(best_f1_scores: List[float], model_results: Dict[str, Dict[str, List[float]]], best_model: str, models_config: Dict[str, str]) -> Dict[str, Any]:
    """Compute Wilcoxon signed-rank tests (non-parametric alternative to t-test)"""
    wilcoxon_tests = {}
    
    for model_type, model_name in models_config.items():
        if model_name != best_model and model_type in model_results:
            other_f1_scores = model_results[model_type]['f1_scores']
            try:
                # Debug logging
                print(f"Wilcoxon {best_model} vs {model_name}:", flush=True)
                print(f"  Best F1 scores: {best_f1_scores}", flush=True)
                print(f"  Other F1 scores: {other_f1_scores}", flush=True)
                
                # Check if scores are identical
                if np.array_equal(best_f1_scores, other_f1_scores):
                    print(f"  Scores are identical", flush=True)
                    wilcoxon_tests[f"{best_model}_vs_{model_name}"] = {
                        "statistic": 0.0,
                        "p_value": 1.0,
                        "significant": False,
                        "note": "Identical scores"
                    }
                else:
                    stat, p_value = stats.wilcoxon(best_f1_scores, other_f1_scores)
                    print(f"  Statistic: {stat}", flush=True)
                    print(f"  P-value: {p_value}", flush=True)
                    wilcoxon_tests[f"{best_model}_vs_{model_name}"] = {
                        "statistic": float(stat),
                        "p_value": float(p_value),
                        "significant": p_value < 0.05
                    }
            except Exception as e:
                print(f"  Error in Wilcoxon test: {str(e)}", flush=True)
                wilcoxon_tests[f"{best_model}_vs_{model_name}"] = {
                    "error": str(e),
                    "significant": False
                }
    
    return wilcoxon_tests


def _compute_mcnemar_tests(y_true: np.ndarray, predictions: Dict[str, np.ndarray], best_model: str) -> Dict[str, Any]:
    """Compute McNemar's test for binary classifier comparison"""
    try:
        from statsmodels.stats.contingency_tables import mcnemar
    except ImportError:
        return {"error": "statsmodels not installed - McNemar's test requires statsmodels package"}
    
    mcnemar_tests = {}
    
    if best_model not in predictions:
        return mcnemar_tests
    
    best_pred = predictions[best_model]
    
    # Validate that best_pred is not None
    if best_pred is None:
        print(f"McNemar test skipped: best_model predictions are None", flush=True)
        return mcnemar_tests
    
    for model_name, pred in predictions.items():
        if model_name != best_model:
            # Validate that pred is not None
            if pred is None:
                print(f"McNemar {best_model} vs {model_name}: skipped - predictions are None", flush=True)
                mcnemar_tests[f"{best_model}_vs_{model_name}"] = {
                    "error": "Predictions are None",
                    "significant": False
                }
                continue
                
            try:
                # Debug logging - check predictions
                print(f"McNemar {best_model} vs {model_name}:", flush=True)
                print(f"  Best pred shape: {best_pred.shape}", flush=True)
                print(f"  Other pred shape: {pred.shape}", flush=True)
                print(f"  Best pred unique values: {np.unique(best_pred)}", flush=True)
                print(f"  Other pred unique values: {np.unique(pred)}", flush=True)
                print(f"  Predictions identical: {np.array_equal(best_pred, pred)}", flush=True)
                print(f"  Best pred sample: {best_pred[:10]}", flush=True)
                print(f"  Other pred sample: {pred[:10]}", flush=True)
                
                # Create contingency table
                # Both correct, Best correct/Other wrong, Best wrong/Other correct, Both wrong
                both_correct = np.sum((best_pred == y_true) & (pred == y_true))
                best_correct = np.sum((best_pred == y_true) & (pred != y_true))
                other_correct = np.sum((best_pred != y_true) & (pred == y_true))
                both_wrong = np.sum((best_pred != y_true) & (pred != y_true))
                
                contingency = [[both_correct, best_correct], [other_correct, both_wrong]]
                
                print(f"  Contingency table: {contingency}", flush=True)
                print(f"  Total disagreements: {best_correct + other_correct}", flush=True)
                
                # Use exact test for small samples or when contingency table has zeros
                total_disagreements = best_correct + other_correct
                if total_disagreements < 25:
                    result = mcnemar(contingency, exact=True)
                    print(f"  Using exact test", flush=True)
                else:
                    result = mcnemar(contingency, exact=False, correction=True)
                    print(f"  Using chi-squared test with correction", flush=True)
                
                print(f"  Statistic: {result.statistic if hasattr(result, 'statistic') else 'N/A'}", flush=True)
                print(f"  P-value: {result.pvalue}", flush=True)
                
                mcnemar_tests[f"{best_model}_vs_{model_name}"] = {
                    "statistic": float(result.statistic) if hasattr(result, 'statistic') else 0.0,
                    "p_value": float(result.pvalue),
                    "significant": result.pvalue < 0.05,
                    "contingency_table": contingency
                }
            except Exception as e:
                print(f"  Error in McNemar test: {str(e)}")
                mcnemar_tests[f"{best_model}_vs_{model_name}"] = {
                    "error": str(e),
                    "significant": False
                }
    
    return mcnemar_tests


def _compute_bootstrap_intervals(scores: List[float], n_bootstrap: int = 1000, confidence: float = 0.95) -> Tuple[float, float]:
    """Compute bootstrap confidence intervals"""
    bootstrap_means = []
    n = len(scores)
    
    for _ in range(n_bootstrap):
        sample = np.random.choice(scores, size=n, replace=True)
        bootstrap_means.append(np.mean(sample))
    
    alpha = (1 - confidence) / 2
    lower = np.percentile(bootstrap_means, alpha * 100)
    upper = np.percentile(bootstrap_means, (1 - alpha) * 100)
    
    return (float(lower), float(upper))


def _compute_variance_analysis(results: List[ModelComparisonResult]) -> Dict[str, Dict[str, float]]:
    """Compute variance analysis for model stability"""
    variance_analysis = {}
    
    for result in results:
        variance_analysis[result.model_name] = {
            "f1_variance": float(np.var(result.f1_scores)),
            "f1_std": float(result.f1_std),
            "f1_cv": float(result.f1_std / result.f1_mean) if result.f1_mean > 0 else 0.0,
            "stability": "Alta" if result.f1_std < 0.05 else "Media" if result.f1_std < 0.1 else "Baja"
        }
    
    return variance_analysis


def _compute_learning_curves(X: np.ndarray, y: np.ndarray, models_config: Dict[str, str]) -> Dict[str, Dict[str, List[float]]]:
    """Compute learning curves for all models"""
    learning_curves = {}
    
    train_sizes = np.linspace(0.1, 1.0, 10)
    
    for model_type, model_name in models_config.items():
        try:
            pipeline = _build_pipeline(model_type)
            
            train_sizes_abs, train_scores, val_scores = learning_curve(
                pipeline, X, y, cv=5, n_jobs=-1,
                train_sizes=train_sizes, scoring='f1'
            )
            
            learning_curves[model_name] = {
                "train_sizes": train_sizes_abs.tolist(),
                "train_scores_mean": np.mean(train_scores, axis=1).tolist(),
                "train_scores_std": np.std(train_scores, axis=1).tolist(),
                "val_scores_mean": np.mean(val_scores, axis=1).tolist(),
                "val_scores_std": np.std(val_scores, axis=1).tolist()
            }
        except Exception as e:
            learning_curves[model_name] = {"error": str(e)}
    
    return learning_curves


def _compute_calibration_curves(X: np.ndarray, y: np.ndarray, predictions: Dict[str, np.ndarray], models_config: Dict[str, str]) -> Dict[str, Dict[str, List[float]]]:
    """Compute calibration curves for models that support predict_proba"""
    calibration_curves = {}
    
    for model_type, model_name in models_config.items():
        try:
            pipeline = _build_pipeline(model_type)
            pipeline.fit(X, y)
            
            if hasattr(pipeline, 'predict_proba'):
                prob_pos = pipeline.predict_proba(X)[:, 1]
                fraction_of_positives, mean_predicted_value = calibration_curve(y, prob_pos, n_bins=10)
                
                calibration_curves[model_name] = {
                    "fraction_of_positives": fraction_of_positives.tolist(),
                    "mean_predicted_value": mean_predicted_value.tolist()
                }
            else:
                calibration_curves[model_name] = {"error": "Model does not support predict_proba"}
        except Exception as e:
            calibration_curves[model_name] = {"error": str(e)}
    
    return calibration_curves


def _compute_feature_importance_stability(results: List[ModelComparisonResult]) -> Dict[str, Dict[str, float]]:
    """Compute stability analysis of feature importance across models"""
    feature_importance_stability = {}
    
    # Collect all features across models
    all_features = set()
    for result in results:
        all_features.update(result.feature_importance.keys())
    
    all_features = sorted(all_features)
    
    # Compute coefficient of variation for each feature across models
    for feature in all_features:
        values = []
        for result in results:
            if feature in result.feature_importance:
                values.append(result.feature_importance[feature])
        
        if values and len(values) > 1:
            values_array = np.array(values)
            mean_val = np.mean(values_array)
            std_val = np.std(values_array)
            
            # Normalize values to 0-1 range before computing CV
            if np.max(values_array) > 0:
                normalized_values = values_array / np.max(values_array)
                mean_normalized = np.mean(normalized_values)
                std_normalized = np.std(normalized_values)
                cv = std_normalized / mean_normalized if mean_normalized > 0 else 0
            else:
                cv = 0
            
            feature_importance_stability[feature] = {
                "mean": float(mean_val),
                "std": float(std_val),
                "cv": float(cv),
                "stability": "Alta" if cv < 0.3 else "Media" if cv < 0.5 else "Baja"
            }
    
    return feature_importance_stability


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
    out_of_fold_predictions = {}  # Store out-of-fold predictions for error analysis

    for model_type, model_name in models_config.items():
        print(f"Evaluating {model_name}...", flush=True)
        
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
        
        # Get out-of-fold predictions for error analysis
        try:
            oof_predictions = cross_val_predict(pipeline, X, y, cv=cv, method='predict')
            out_of_fold_predictions[model_name] = oof_predictions
            print(f"Out-of-fold predictions for {model_name}: shape={oof_predictions.shape}", flush=True)
        except Exception as e:
            print(f"Error getting out-of-fold predictions for {model_name}: {str(e)}", flush=True)
            out_of_fold_predictions[model_name] = None
        
        # Compute feature importance
        feature_importance = _compute_feature_importance(pipeline, model_type)

        # Extract hyperparameters
        hyperparameters = {}
        classifier = pipeline.named_steps['classifier']
        for param, value in classifier.get_params().items():
            if not param.startswith('_'):
                hyperparameters[param] = value

        # Compute confusion matrix on full dataset
        y_pred = pipeline.predict(X)
        cm = confusion_matrix(y, y_pred)
        confusion_matrix_list = cm.tolist()

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
            feature_importance=feature_importance,
            hyperparameters=hyperparameters,
            confusion_matrix=confusion_matrix_list
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
                # Check if scores are identical
                if np.array_equal(best_f1_scores, other_f1_scores):
                    statistical_tests[f"{best_model}_vs_{result.model_name}"] = {
                        "t_statistic": 0.0,
                        "p_value": 1.0,
                        "significant": False,
                        "note": "Identical scores"
                    }
                else:
                    t_stat, p_value = stats.ttest_rel(best_f1_scores, other_f1_scores)
                    statistical_tests[f"{best_model}_vs_{result.model_name}"] = {
                        "t_statistic": float(t_stat) if not np.isnan(t_stat) else 0.0,
                        "p_value": float(p_value) if not np.isnan(p_value) else 1.0,
                        "significant": p_value < 0.05
                    }

    # Additional statistical tests
    wilcoxon_tests = _compute_wilcoxon_tests(best_f1_scores, model_results, best_model, models_config) if best_f1_scores is not None and len(best_f1_scores) > 0 else {}
    
    mcnemar_tests = _compute_mcnemar_tests(y, out_of_fold_predictions, best_model) if out_of_fold_predictions is not None else {}
    
    # Bootstrap confidence intervals for all models
    bootstrap_intervals = {}
    for result in results:
        lower, upper = _compute_bootstrap_intervals(result.f1_scores)
        bootstrap_intervals[result.model_name] = {
            "f1_lower": lower,
            "f1_upper": upper
        }
    
    # Variance analysis for model stability
    variance_analysis = _compute_variance_analysis(results)
    
    # Learning curves
    learning_curves = _compute_learning_curves(X, y, models_config)
    
    # Calibration curves
    calibration_curves = _compute_calibration_curves(X, y, out_of_fold_predictions, models_config)
    
    # Feature importance stability
    feature_importance_stability = _compute_feature_importance_stability(results)

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
        roc_curves=roc_curves,
        out_of_fold_predictions=out_of_fold_predictions,
        wilcoxon_tests=wilcoxon_tests,
        mcnemar_tests=mcnemar_tests,
        bootstrap_intervals=bootstrap_intervals,
        variance_analysis=variance_analysis,
        learning_curves=learning_curves,
        calibration_curves=calibration_curves,
        feature_importance_stability=feature_importance_stability
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


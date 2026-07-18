# Módulo de Machine Learning - Scoring de Riesgo de Morosidad

Este módulo implementa un sistema de comparación de modelos de machine learning para predecir el riesgo de morosidad de clientes en un sistema de facturación electrónica.

## Arquitectura

### Modelos Implementados

El sistema compara 5 modelos de machine learning usando scikit-learn:

1. **Logistic Regression** - Baseline interpretable con coeficientes explicativos
2. **Random Forest** - Ensemble robusto con feature importance intrínseco
3. **Support Vector Machine (SVM)** - Kernel methods para fronteras complejas
4. **Gradient Boosting** - State-of-the-art para datos tabulares
5. **Neural Network (MLP)** - Multi-layer perceptron para deep learning básico

### Features del Modelo

El sistema calcula 6 features por cliente:

- `pct_facturas_vencidas`: Proporción de facturas resueltas que terminaron vencidas
- `pct_pagos_tardios`: Proporción de facturas pagadas con pago posterior a vencimiento
- `dias_mora_promedio`: Promedio de días de mora
- `monto_promedio_factura`: Monto promedio de facturas
- `cantidad_facturas`: Cantidad de facturas resueltas
- `antiguedad_dias`: Días desde el registro del cliente

### Etiqueta de Entrenamiento

Label binario: 1 si `pct_facturas_vencidas > 0.34` o `pct_pagos_tardios > 0.34`, si no 0.

## Metodología de Evaluación

### Cross-Validation

- **10-fold stratified cross-validation** para evaluación robusta
- Random state fijo (42) para reproducibilidad
- Shuffle de datos antes de dividir

### Métricas Evaluadas

Para cada modelo se calculan:

- **F1-Score**: Métrica principal (balancea precision y recall)
- **Accuracy**: Exactitud general
- **Precision**: Precisión de predicciones positivas
- **Recall**: Sensibilidad para detectar alto riesgo
- **ROC-AUC**: Área bajo la curva ROC
- **Training Time**: Tiempo de entrenamiento en segundos

### Visualizaciones Implementadas

**1. Matriz de Correlación de Features**
- Heatmap mostrando correlaciones entre las 6 features
- Colores: rojo (positiva), azul (negativa), gris (débil)
- Útil para análisis exploratorio de datos

**2. Curvas ROC Comparativas**
- Curvas ROC superpuestas para los 5 modelos
- Muestra trade-off entre sensibilidad y especificidad
- Incluye AUC para cada modelo

**3. Feature Importance Comparativo**
- Gráfico de barras horizontal comparando importancia de features
- Muestra cómo cada modelo pondera las features
- Facilita comparación de interpretación entre modelos

### Pruebas Estadísticas

- **t-test pareado** entre el mejor modelo y los demás
- **p-value < 0.05** indica diferencia estadísticamente significativa
- Intervalos de confianza: mean ± 2*std

### Feature Importance

- **Logistic Regression**: Coeficientes escalados por desviación estándar
- **Random Forest**: Feature importance intrínseco del modelo
- **Gradient Boosting**: Feature importance del ensemble
- **SVM/MLP**: Pesos iguales (no tienen feature importance directo)

## Uso del Sistema

### Comparación de Modelos

```python
from app.ml.risk_model import compare_models
from app.ml.features import compute_client_features

# Construir dataset desde la base de datos
dataset = []
for client in clients:
    features = compute_client_features(client, invoices, payments_by_invoice)
    if features:
        dataset.append(features)

# Comparar modelos
result = compare_models(dataset)

# Resultados
print(f"Mejor modelo: {result.best_model}")
print(f"F1-Score: {result.best_f1}")
print(f"Recomendación: {result.recommendation}")

# Tabla comparativa
for model_result in result.results:
    print(f"{model_result.model_name}: F1={model_result.f1_mean:.3f} ± {model_result.f1_std:.3f}")
```

### Entrenamiento de Modelo Específico

```python
from app.ml.risk_model import train_model_with_type

# Entrenar Gradient Boosting (mejor modelo típico)
result = train_model_with_type(dataset, "gradient_boosting")

# Otros modelos disponibles:
# - "logistic"
# - "random_forest"
# - "svm"
# - "mlp"
```

### Predicción con Modelo Entrenado

```python
from app.ml.risk_model import predict_proba

# Calcular features del cliente
features = compute_client_features(client, invoices, payments_by_invoice)

# Predecir probabilidad de alto riesgo
probability = predict_proba(features)  # 0.0 a 1.0
```

## API Endpoints

### POST /api/risk/compare-models

Compara los 5 modelos usando cross-validation.

**Permisos:** Administrador o Contador

**Response:**
```json
{
  "results": [
    {
      "model_name": "Gradient Boosting",
      "f1_mean": 0.85,
      "f1_std": 0.05,
      "accuracy_mean": 0.82,
      "accuracy_std": 0.06,
      "precision_mean": 0.83,
      "precision_std": 0.07,
      "recall_mean": 0.87,
      "recall_std": 0.08,
      "roc_auc_mean": 0.89,
      "roc_auc_std": 0.04,
      "training_time": 2.5,
      "feature_importance": {
        "pct_facturas_vencidas": 35.2,
        "pct_pagos_tardios": 28.1,
        "dias_mora_promedio": 18.5,
        "monto_promedio_factura": 8.3,
        "cantidad_facturas": 6.2,
        "antiguedad_dias": 3.7
      }
    }
  ],
  "best_model": "Gradient Boosting",
  "best_f1": 0.85,
  "recommendation": "El modelo Gradient Boosting muestra un rendimiento excelente (F1=0.850). Se recomienda su implementación en producción.",
  "statistical_tests": {
    "Gradient Boosting_vs_Logistic Regression": {
      "t_statistic": 3.45,
      "p_value": 0.0023,
      "significant": true
    }
  }
}
```

### POST /api/risk/train-with-type

Entrena un modelo específico y lo persiste.

**Request:**
```json
{
  "model_type": "gradient_boosting"
}
```

**Permisos:** Administrador o Contador

## Reproducibilidad para Artículo

### Configuración del Entorno

```bash
# Instalar dependencias
pip install -r requirements.txt

# Dependencias clave de ML:
# scikit-learn==1.5.2
# joblib==1.4.2
# numpy==2.1.2
# scipy>=1.11.0
```

### Generación de Datos de Demo

```bash
# Generar datos de demostración
python scripts/seed_demo_data.py

# Esto crea 30 clientes con diferentes perfiles de pago:
# - 40% buenos pagadores
# - 35% pagadores intermedios
# - 25% malos pagadores
```

### Ejecución de Comparación de Modelos

1. **Iniciar el backend:**
```bash
cd backend
uvicorn app.main:app --reload
```

2. **Ejecutar comparación:**
   - Ir a http://localhost:8000/docs
   - Autenticarse como administrador
   - Ejecutar POST /api/risk/compare-models

3. **O usar el frontend:**
   - Ir a la página de Riesgo
   - Hacer clic en "Comparar Modelos"
   - Ver resultados en la tabla comparativa

### Resultados Esperados

Con los datos de demo (`seed_demo_data.py`), deberías obtener:

- **Mejor modelo**: Gradient Boosting o Random Forest
- **F1-Score**: 0.70-0.85 (dependiendo de la aleatoriedad de los datos)
- **Diferencia significativa** entre modelos ensemble y lineales
- **Feature importance**: `pct_facturas_vencidas` y `pct_pagos_tardios` como más importantes

## Referencias para Artículo

### Metodología

- **Cross-validation**: Kohavi, R. (1995). "A study of cross-validation and bootstrap for accuracy estimation and model selection"
- **Feature importance**: Breiman, L. (2001). "Random Forests" para feature importance en ensemble methods
- **Statistical tests**: Demsar, J. (2006). "Statistical comparisons of classifiers over multiple data sets"

### Modelos

- **Logistic Regression**: Hosmer, D. W., & Lemeshow, S. (2000). "Applied Logistic Regression"
- **Random Forest**: Breiman, L. (2001). "Random Forests" 
- **SVM**: Cortes, C., & Vapnik, V. (1995). "Support-vector networks"
- **Gradient Boosting**: Friedman, J. H. (2001). "Greedy function approximation: a gradient boosting machine"
- **Neural Networks**: Goodfellow, I., et al. (2016). "Deep Learning"

### Credit Scoring

- **Feature engineering**: Thomas, L. C., et al. (2002). "Credit Scoring and Its Applications"
- **Risk assessment**: Siddiqi, N. (2006). "Credit Risk Scorecards: Developing and Implementing Intelligent Credit Scoring"

## Estructura de Archivos

```
app/ml/
├── __init__.py
├── features.py              # Cálculo de features del cliente
├── risk_model.py            # Modelos de ML y comparación
├── model_artifacts/         # Modelos persistidos (.gitignore)
│   └── risk_model.joblib    # Modelo entrenado actual
└── README.md               # Este archivo
```

## Notas de Implementación

- **Random state**: Fijado en 42 para reproducibilidad
- **Class weight**: "balanced" para manejar datasets desbalanceados
- **Max iterations**: 1000 para Logistic Regression y MLP
- **N estimators**: 100 para ensemble methods
- **Early stopping**: Activado para MLP para evitar overfitting

## Limitaciones y Futuras Mejoras

### Limitaciones Actuales

- SVM y MLP no tienen feature importance directo
- No se implementó calibración de probabilidades
- No se incluyó hyperparameter tuning

### Mejoras Futuras

- **Hyperparameter optimization**: Grid search u Optuna
- **Calibration**: Isotonic regression o Platt scaling
- **Advanced models**: XGBoost, LightGBM, CatBoost
- **Explainability**: SHAP values para interpretación local
- **Ensemble stacking**: Combinar múltiples modelos
- **Time series**: Incorporar tendencias temporales

## Contacto

Para preguntas sobre la implementación o reproducción de resultados, consultar el repositorio del proyecto.

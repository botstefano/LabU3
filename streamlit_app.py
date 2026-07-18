import streamlit as st
import sys
import os
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent / "backend"))

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from sqlalchemy import create_engine
from app.ml.risk_model import compare_models, _build_pipeline, _compute_correlation_matrix, _compute_roc_curves
from app.ml.features import compute_client_features, features_to_vector, FEATURE_NAMES
from app.repositories.client_repository import ClientRepository
from app.repositories.invoice_repository import InvoiceRepository
from app.repositories.payment_repository import PaymentRepository
from app.services.invoice_service import InvoiceService
from app.db.database import get_db

# Page config
st.set_page_config(
    page_title="ML Risk Scoring",
    page_icon="🧠",
    layout="wide"
)

# Database connection
@st.cache_resource
def get_db_engine():
    from app.core.config import get_settings
    settings = get_settings()
    return create_engine(settings.database_url)

def load_data():
    """Load data from database"""
    engine = get_db_engine()
    
    # Get clients
    clients_df = pd.read_sql("SELECT * FROM clients", engine)
    
    # Get invoices
    invoices_df = pd.read_sql("SELECT * FROM invoices", engine)
    
    # Get payments
    payments_df = pd.read_sql("SELECT * FROM payments", engine)
    
    return clients_df, invoices_df, payments_df

def compute_features_from_db(clients_df, invoices_df, payments_df):
    """Compute features from database data"""
    dataset = []
    
    for _, client in clients_df.iterrows():
        client_invoices = invoices_df[invoices_df['client_id'] == client['id']]
        
        payments_by_invoice = {}
        for _, inv in client_invoices.iterrows():
            invoice_payments = payments_df[payments_df['invoice_id'] == inv['id']]
            payments_by_invoice[str(inv['id'])] = invoice_payments.to_dict('records')
        
        # Convert to SQLAlchemy-like objects
        from app.models.client import Client
        from app.models.invoice import Invoice
        from app.models.payment import Payment
        
        client_obj = Client(
            id=client['id'],
            tipo_documento=client['tipo_documento'],
            numero_documento=client['numero_documento'],
            nombre_razon_social=client['nombre_razon_social'],
            email=client['email'],
            telefono=client['telefono'],
            created_at=client['created_at']
        )
        
        invoices_obj = []
        for _, inv in client_invoices.iterrows():
            inv_obj = Invoice(
                id=inv['id'],
                numero=inv['numero'],
                client_id=inv['client_id'],
                fecha_emision=inv['fecha_emision'],
                fecha_vencimiento=inv['fecha_vencimiento'],
                subtotal=inv['subtotal'],
                igv=inv['igv'],
                total=inv['total'],
                estado=inv['estado'],
                created_at=inv['created_at']
            )
            invoices_obj.append(inv_obj)
        
        features = compute_client_features(client_obj, invoices_obj, payments_by_invoice)
        if features:
            dataset.append(features)
    
    return dataset

def main():
    st.title("🧠 ML Risk Scoring - Model Comparison")
    st.markdown("Sistema de comparación de modelos de machine learning para scoring de riesgo de morosidad")
    
    # Load data
    with st.spinner("Cargando datos de la base de datos..."):
        try:
            clients_df, invoices_df, payments_df = load_data()
            dataset = compute_features_from_db(clients_df, invoices_df, payments_df)
            
            if len(dataset) < 12:
                st.error("No hay suficientes datos para entrenar modelos. Ejecuta `python scripts/seed_demo_data.py` primero.")
                return
            
            st.success(f"Datos cargados: {len(dataset)} clientes con historial")
        except Exception as e:
            st.error(f"Error cargando datos: {e}")
            return
    
    # Compare models
    st.header("Comparación de Modelos")
    
    if st.button("Comparar 5 Modelos", type="primary"):
        with st.spinner("Comparando modelos con cross-validation 10-fold..."):
            result = compare_models(dataset)
            
            # Display best model
            st.subheader("Mejor Modelo")
            col1, col2, col3 = st.columns(3)
            col1.metric("Modelo", result.best_model)
            col2.metric("F1-Score", f"{result.best_f1:.3f}")
            col3.metric("Estado", "Excelente" if result.best_f1 > 0.8 else "Bueno" if result.best_f1 > 0.7 else "Moderado")
            
            st.info(result.recommendation)
            
            # Comparison table
            st.subheader("Tabla Comparativa")
            results_df = pd.DataFrame([
                {
                    "Modelo": r.model_name,
                    "F1": f"{r.f1_mean:.3f} ± {r.f1_std:.3f}",
                    "Accuracy": f"{r.accuracy_mean:.3f} ± {r.accuracy_std:.3f}",
                    "Precision": f"{r.precision_mean:.3f} ± {r.precision_std:.3f}",
                    "Recall": f"{r.recall_mean:.3f} ± {r.recall_std:.3f}",
                    "ROC-AUC": f"{r.roc_auc_mean:.3f} ± {r.roc_auc_std:.3f}",
                    "Tiempo (s)": f"{r.training_time:.2f}"
                }
                for r in result.results
            ])
            st.dataframe(results_df, use_container_width=True)
            
            # Statistical tests
            if result.statistical_tests:
                st.subheader("Tests Estadísticos (t-test pareado)")
                tests_df = pd.DataFrame([
                    {
                        "Comparación": test,
                        "t-statistic": f"{data['t_statistic']:.3f}",
                        "p-value": f"{data['p_value']:.4f}",
                        "Significativo": "✅" if data['significant'] else "❌"
                    }
                    for test, data in result.statistical_tests.items()
                ])
                st.dataframe(tests_df, use_container_width=True)
            
            # Correlation heatmap
            if result.correlation_matrix:
                st.subheader("Matriz de Correlación de Features")
 
                corr_df = pd.DataFrame(result.correlation_matrix)
                fig = px.imshow(
                    corr_df,
                    text_auto=True,
                    aspect="auto",
                    color_continuous_scale='RdBu_r',
                    range_color=[-1, 1]
                )
                fig.update_layout(title="Correlación entre Features")
                st.plotly_chart(fig, use_container_width=True)
            
            # ROC curves
            if result.roc_curves:
                st.subheader("Curvas ROC Comparativas")
                
                fig = go.Figure()
                colors = ['#3b82f6', '#ef4444', '#10b981', '#f59e0b', '#8b5cf6']
                
                for i, (model_name, data) in enumerate(result.roc_curves.items()):
                    fig.add_trace(go.Scatter(
                        x=data['fpr'],
                        y=data['tpr'],
                        mode='lines',
                        name=f"{model_name} (AUC: {data['auc']:.3f})",
                        line=dict(color=colors[i], width=2)
                    ))
                
                fig.add_trace(go.Scatter(
                    x=[0, 1],
                    y=[0, 1],
                    mode='lines',
                    name='Random',
                    line=dict(color='gray', width=1, dash='dash')
                ))
                
                fig.update_layout(
                    title="Curvas ROC",
                    xaxis_title="False Positive Rate",
                    yaxis_title="True Positive Rate",
                    legend=dict(x=0.7, y=0.1)
                )
                st.plotly_chart(fig, use_container_width=True)
            
            # Feature importance comparison
            st.subheader("Comparación de Feature Importance")
            
            feature_importance_data = []
            for result_item in result.results:
                for feature, importance in result_item.feature_importance.items():
                    feature_importance_data.append({
                        "Feature": feature,
                        "Modelo": result_item.model_name,
                        "Importancia": importance
                    })
            
            fi_df = pd.DataFrame(feature_importance_data)
            fig = px.bar(fi_df, x="Importancia", y="Feature", color="Modelo", orientation="h", barmode="group")
            fig.update_layout(title="Feature Importance por Modelo", height=500)
            st.plotly_chart(fig, use_container_width=True)

if __name__ == "__main__":
    main()

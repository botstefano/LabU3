import streamlit as st
import sys
import os
from pathlib import Path
from datetime import datetime
from io import BytesIO

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent / "backend"))

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from sklearn.metrics import f1_score, precision_score, recall_score
from sqlalchemy import create_engine
from app.ml.risk_model import compare_models, _compute_correlation_matrix, _compute_roc_curves
from app.ml.features import compute_client_features, features_to_vector, FEATURE_NAMES
from app.repositories.client_repository import ClientRepository
from app.repositories.invoice_repository import InvoiceRepository
from app.repositories.payment_repository import PaymentRepository
from app.services.invoice_service import InvoiceService
from app.db.database import get_db

try:
    from reportlab.lib.pagesizes import letter
    from reportlab.lib import colors
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.enums import TA_CENTER, TA_LEFT
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False

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
    try:
        settings = get_settings()
        engine = create_engine(settings.database_url)
        # Test connection
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return engine
    except Exception as e:
        st.error(f"❌ Error conectando a la base de datos: {e}")
        st.error("Verifica que DATABASE_URL esté configurado correctamente en .env")
        raise

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
    """Compute features from database data using vectorized operations for better scalability"""
    from app.models.client import Client
    from app.models.invoice import Invoice
    from app.models.payment import Payment
    from datetime import datetime

    dataset = []

    # Vectorized approach: group by client_id
    # Group invoices by client
    invoices_grouped = invoices_df.groupby('client_id')
    
    # Group payments by invoice_id
    payments_grouped = payments_df.groupby('invoice_id')

    for _, client in clients_df.iterrows():
        client_id = client['id']
        
        # Get client invoices using groupby (faster than filtering)
        if client_id not in invoices_grouped.groups:
            continue
            
        client_invoices = invoices_grouped.get_group(client_id)
        
        # Build payments_by_invoice using vectorized operations
        payments_by_invoice = {}
        for inv_id in client_invoices['id']:
            if inv_id in payments_grouped.groups:
                invoice_payments = payments_grouped.get_group(inv_id)
                payment_objs = []
                for _, pay in invoice_payments.iterrows():
                    payment_obj = Payment(
                        id=pay['id'],
                        invoice_id=pay['invoice_id'],
                        fecha_pago=pay['fecha_pago'],
                        monto=pay['monto'],
                        metodo_pago=pay['metodo_pago'],
                        registrado_por=pay['registrado_por'],
                        created_at=pay['created_at']
                    )
                    payment_objs.append(payment_obj)
                payments_by_invoice[str(inv_id)] = payment_objs
        
        # Create client object
        client_obj = Client(
            id=client['id'],
            tipo_documento=client['tipo_documento'],
            numero_documento=client['numero_documento'],
            nombre_razon_social=client['nombre_razon_social'],
            email=client['email'],
            telefono=client['telefono'],
            created_at=client['created_at']
        )
        
        # Create invoice objects
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
                created_by=inv['created_by'] if 'created_by' in inv else client['id'],
                created_at=inv['created_at']
            )
            invoices_obj.append(inv_obj)
        
        features = compute_client_features(client_obj, invoices_obj, payments_by_invoice)
        if features:
            dataset.append(features)
    
    return dataset

def generate_pdf_report(result, dataset_size, data_source):
    """Generate PDF report with training results"""
    if not REPORTLAB_AVAILABLE:
        return None

    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    styles = getSampleStyleSheet()

    # Custom styles
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=18,
        textColor=colors.HexColor('#1e88e5'),
        alignment=TA_CENTER,
        spaceAfter=30
    )

    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontSize=14,
        textColor=colors.HexColor('#333333'),
        spaceAfter=12
    )

    content = []

    # Title
    content.append(Paragraph("Reporte de Entrenamiento de Modelos ML", title_style))
    content.append(Spacer(1, 12))

    # Date and source
    content.append(Paragraph(f"<b>Fecha:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", styles['Normal']))
    content.append(Paragraph(f"<b>Fuente de datos:</b> {data_source}", styles['Normal']))
    content.append(Paragraph(f"<b>Tamaño del dataset:</b> {dataset_size} muestras", styles['Normal']))
    content.append(Spacer(1, 12))

    # Best Model
    content.append(Paragraph("Mejor Modelo", heading_style))
    best_model_data = [
        ["Modelo", result.best_model],
        ["F1-Score", f"{result.best_f1:.3f}"],
        ["Estado", "Excelente" if result.best_f1 > 0.8 else "Bueno" if result.best_f1 > 0.7 else "Moderado"]
    ]
    best_model_table = Table(best_model_data, colWidths=[3, 2])
    best_model_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#e3f2fd')),
        ('TEXTCOLOR', (0, 0), (0, -1), colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (1, 0), (1, -1), colors.HexColor('#f5f5f5')),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
    ]))
    content.append(best_model_table)
    content.append(Spacer(1, 12))

    # Recommendation
    content.append(Paragraph("Recomendación", heading_style))
    content.append(Paragraph(result.recommendation, styles['Normal']))
    content.append(Spacer(1, 12))

    # Comparison Table
    content.append(Paragraph("Tabla Comparativa", heading_style))
    comparison_data = [["Modelo", "F1", "Accuracy", "Precision", "Recall", "ROC-AUC", "Tiempo (s)"]]
    for r in result.results:
        comparison_data.append([
            r.model_name,
            f"{r.f1_mean:.3f} ± {r.f1_std:.3f}",
            f"{r.accuracy_mean:.3f} ± {r.accuracy_std:.3f}",
            f"{r.precision_mean:.3f} ± {r.precision_std:.3f}",
            f"{r.recall_mean:.3f} ± {r.recall_std:.3f}",
            f"{r.roc_auc_mean:.3f} ± {r.roc_auc_std:.3f}",
            f"{r.training_time:.2f}"
        ])

    comparison_table = Table(comparison_data, colWidths=[2.5, 1, 1, 1, 1, 1, 0.8])
    comparison_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1e88e5')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 9),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.white),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f5f5f5')]),
    ]))
    content.append(comparison_table)
    content.append(Spacer(1, 12))

    # Statistical Tests
    if result.statistical_tests:
        content.append(Paragraph("Tests Estadísticos", heading_style))
        tests_data = [["Test", "p-value", "Significativo"]]
        for test_name, test_data in result.statistical_tests.items():
            tests_data.append([
                test_name,
                f"{test_data['p_value']:.4f}",
                "Sí" if test_data['significant'] else "No"
            ])

        tests_table = Table(tests_data, colWidths=[3, 1.5, 1.5])
        tests_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1e88e5')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.white),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f5f5f5')]),
        ]))
        content.append(tests_table)
        content.append(Spacer(1, 12))

    # Build PDF
    doc.build(content)
    buffer.seek(0)
    return buffer

def main():
    # Page configuration
    st.set_page_config(
        page_title="ML Risk Scoring",
        page_icon="🧠",
        layout="wide",
        initial_sidebar_state="expanded"
    )

    # Custom CSS for professional styling
    st.markdown("""
    <style>
    :root {
        --color-primary: #2c3e50;
        --color-secondary: #34495e;
        --color-accent: #3498db;
        --color-success: #27ae60;
        --color-warning: #f39c12;
        --color-danger: #c0392b;
        --color-light: #ecf0f1;
        --color-dark: #2c3e50;
        --color-text: #333333;
        --color-text-muted: #7f8c8d;
        --border-radius: 8px;
        --spacing-sm: 0.5rem;
        --spacing-md: 1rem;
        --spacing-lg: 2rem;
    }
    
    .main-header {
        font-size: 2rem;
        font-weight: 700;
        color: var(--color-primary);
        margin-bottom: var(--spacing-sm);
    }
    
    .sub-header {
        font-size: 1rem;
        color: var(--color-text-muted);
        margin-bottom: var(--spacing-lg);
    }
    
    .section-header {
        font-size: 1.5rem;
        font-weight: 600;
        color: var(--color-primary);
        margin-top: var(--spacing-lg);
        margin-bottom: var(--spacing-md);
        border-bottom: 2px solid var(--color-accent);
        padding-bottom: var(--spacing-sm);
    }
    
    .metric-card {
        background: var(--color-light);
        padding: var(--spacing-md);
        border-radius: var(--border-radius);
        border-left: 4px solid var(--color-accent);
        margin: var(--spacing-sm) 0;
    }
    
    .metric-card.success {
        border-left-color: var(--color-success);
    }
    
    .metric-card.warning {
        border-left-color: var(--color-warning);
    }
    
    .metric-card.danger {
        border-left-color: var(--color-danger);
    }
    
    .info-box {
        background: var(--color-light);
        padding: var(--spacing-md);
        border-radius: var(--border-radius);
        border-left: 4px solid var(--color-accent);
        margin: var(--spacing-sm) 0;
    }
    
    .feature-description {
        font-size: 0.85rem;
        color: var(--color-text-muted);
        margin-top: var(--spacing-sm);
    }
    
    .methodology-box {
        background: #f8f9fa;
        padding: var(--spacing-md);
        border-radius: var(--border-radius);
        border: 1px solid #dee2e6;
        margin: var(--spacing-md) 0;
    }
    
    .stDataFrame {
        margin-top: var(--spacing-md);
        margin-bottom: var(--spacing-md);
    }
    </style>
    """, unsafe_allow_html=True)

    # Sidebar navigation
    with st.sidebar:
        st.markdown("""
        <div style='text-align: center; padding: 20px 0;'>
            <h1 style='color: #1e88e5; font-size: 1.8rem; font-weight: 700;'>🧠 ML Risk Scoring</h1>
            <p style='color: #666; font-size: 0.9rem;'>Sistema de Evaluación de Riesgo</p>
        </div>
        """, unsafe_allow_html=True)

        st.divider()

        st.markdown("### 📊 Navegación")

        if 'page' not in st.session_state:
            st.session_state.page = "🏠 Inicio"

        page = st.radio(
            "Selecciona una sección:",
            ["🏠 Inicio", "📁 Cargar Datos", "📈 Análisis Dataset", "🤖 Entrenamiento", "📋 Resultados"],
            label_visibility="collapsed",
            index=["🏠 Inicio", "📁 Cargar Datos", "📈 Análisis Dataset", "🤖 Entrenamiento", "📋 Resultados"].index(st.session_state.page)
        )
        st.session_state.page = page

        st.divider()

        st.markdown("### ℹ️ Información")
        st.markdown("""
        **Versión:** 1.0.0
        **Estado:** Producción
        **Última actualización:** 2026-07-18
        """)

        st.divider()

        st.markdown("### 📚 Documentación")
        st.markdown("""
        Este sistema permite:
        - Comparar 5 modelos ML
        - Análisis detallado de datos
        - Evaluación de performance
        - Exportación de reportes
        """)

    # Main content based on selected page
    if page == "🏠 Inicio":
        st.markdown("<h1 class='main-header'>ML Risk Scoring</h1>", unsafe_allow_html=True)
        st.markdown("<p class='sub-header'>Sistema profesional de comparación de modelos de machine learning para scoring de riesgo de morosidad</p>", unsafe_allow_html=True)

        # Project Summary Card (capturable for article)
        st.container(border=True).markdown("""
        ### 📋 Resumen del Proyecto
        
        **Objetivo:** Desarrollar un sistema automatizado de scoring de riesgo de morosidad que predice la probabilidad de impago de clientes basándose en su historial de facturación y pagos.
        
        **Metodología:** Comparación de 5 modelos de machine learning (Logistic Regression, Random Forest, SVM, Gradient Boosting, MLP) utilizando validación cruzada estratificada y 6 features de comportamiento de pago.
        
        **Features Utilizadas:**
        - `pct_facturas_vencidas`: Porcentaje de facturas que superaron su fecha de vencimiento sin pago
        - `pct_pagos_tardios`: Porcentaje de pagos realizados después de la fecha de vencimiento
        - `dias_mora_promedio`: Promedio de días de retraso en los pagos
        - `monto_promedio_factura`: Valor promedio de las facturas emitidas
        - `cantidad_facturas`: Número total de facturas del cliente
        - `antiguedad_dias`: Antigüedad del cliente en días desde su primera factura
        
        **Modelos Comparados:** Logistic Regression, Random Forest, Support Vector Machine, Gradient Boosting, Neural Network (MLP)
        
        **Métricas de Evaluación:** F1-Score, Accuracy, Precision, Recall, ROC-AUC (con validación cruzada estratificada)
        """)

        st.divider()

        # KPIs in grid layout
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.container(border=True).metric("🤖 Modelos", "5", "ML algorithms")
            
        with col2:
            st.container(border=True).metric("📊 Features", "6", "Client features")
            
        with col3:
            st.container(border=True).metric("📈 Métricas", "5", "Evaluation metrics")
            
        with col4:
            st.container(border=True).metric("📄 Exportación", "PDF", "Professional reports")

        st.divider()

        # Features and Models in grid
        col1, col2 = st.columns(2)

        with col1:
            st.container(border=True).markdown("""
            ### 📁 Gestión de Datos
            - **Carga CSV:** Importación de datasets iniciales
            - **Entrenamiento Incremental:** Actualización desde base de datos
            - **Análisis EDA:** Estadísticas descriptivas y distribuciones
            - **Validación:** Detección de datos faltantes y outliers
            """)

        with col2:
            st.container(border=True).markdown("""
            ### 🤖 Modelos ML Comparados
            - **Logistic Regression:** Baseline interpretable
            - **Random Forest:** Ensemble de árboles de decisión
            - **SVM:** Máquinas de vectores de soporte
            - **Gradient Boosting:** Boosting secuencial
            - **MLP:** Red neuronal multicapa
            """)

        st.divider()

        # Workflow
        st.container(border=True).markdown("""
        ### � Flujo de Trabajo
        
        1. **📁 Cargar Datos** → Seleccionar fuente (CSV o base de datos)
        2. **📈 Análisis Dataset** → Explorar estadísticas y distribuciones de features
        3. **🤖 Entrenamiento** → Comparar 5 modelos con cross-validation estratificada
        4. **📋 Resultados** → Analizar métricas, seleccionar mejor modelo y exportar reportes
        """)

        if st.button("Comenzar →", type="primary", use_container_width=True):
            st.session_state.page = "📁 Cargar Datos"
            st.rerun()

    elif page == "📁 Cargar Datos":
        st.markdown("<h1 class='section-header'>Carga de Datos</h1>", unsafe_allow_html=True)

        data_source = st.radio(
            "Selecciona la fuente de datos para el entrenamiento:",
            ["📊 Base de Datos (Incremental)", "📄 Archivo CSV (Primer entrenamiento)"],
            horizontal=True,
            label_visibility="visible"
        )

        dataset = None

        if data_source == "📄 Archivo CSV (Primer entrenamiento)":
            uploaded_file = st.file_uploader("Cargar archivo CSV con dataset inicial", type=['csv'])

            if uploaded_file:
                try:
                    from app.ml.features import ClientFeatures

                    df = pd.read_csv(uploaded_file)
                    dataset = []

                    failed_rows = 0
                    for _, row in df.iterrows():
                        try:
                            features = ClientFeatures(
                                pct_facturas_vencidas=float(row['pct_facturas_vencidas']),
                                pct_pagos_tardios=float(row['pct_pagos_tardios']),
                                dias_mora_promedio=float(row['dias_mora_promedio']),
                                monto_promedio_factura=float(row['monto_promedio_factura']),
                                cantidad_facturas=int(row['cantidad_facturas']),
                                antiguedad_dias=int(row['antiguedad_dias']),
                                label=int(row['label']) if 'label' in row and pd.notna(row['label']) else None
                            )
                            dataset.append(features)
                        except Exception as e:
                            st.warning(f"Omitiendo fila inválida: {e}")
                            failed_rows += 1
                            continue

                    st.success(f"✅ Dataset cargado desde CSV: {len(dataset)} de {len(df)} filas ({failed_rows} fallidas)")
                    st.session_state.dataset = dataset
                    st.session_state.data_source = "CSV"
                    st.session_state.dataset_size = len(dataset)

                except Exception as e:
                    st.error(f"❌ Error cargando CSV: {e}")
                    return
            else:
                st.info("📄 Por favor carga un archivo CSV para el primer entrenamiento.")
                return
        else:
            # Load from database for incremental training
            with st.spinner("Cargando datos de la base de datos..."):
                try:
                    clients_df, invoices_df, payments_df = load_data()
                    dataset = compute_features_from_db(clients_df, invoices_df, payments_df)

                    if len(dataset) < 12:
                        st.warning(f"⚠️ Solo hay {len(dataset)} clientes en la base de datos. Se combinarán con datos guardados.")

                    st.success(f"✅ Datos cargados de BD: {len(dataset)} clientes")
                    st.session_state.dataset = dataset
                    st.session_state.data_source = "Base de Datos"
                    st.session_state.dataset_size = len(dataset)
                except Exception as e:
                    st.error(f"❌ Error cargando datos: {e}")
                    return

        if dataset:
            st.success("🎯 Datos cargados exitosamente. Puedes proceder al análisis del dataset.")
            if st.button("Ir a Análisis de Dataset →", type="primary", use_container_width=True):
                st.session_state.page = "📈 Análisis Dataset"
                st.rerun()

    elif page == "📈 Análisis Dataset":
        st.markdown("<h1 class='section-header'>Análisis del Dataset</h1>", unsafe_allow_html=True)

        if 'dataset' not in st.session_state or st.session_state.dataset is None:
            st.warning("⚠️ Primero debes cargar los datos en la sección 'Cargar Datos'.")
            if st.button("Ir a Cargar Datos", use_container_width=True):
                st.session_state.page = "📁 Cargar Datos"
                st.rerun()
            return

        dataset = st.session_state.dataset

        # Convert dataset to DataFrame for analysis
        dataset_df = pd.DataFrame([
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
        ])

        # Feature descriptions for documentation
        feature_descriptions = {
            "pct_facturas_vencidas": "Porcentaje de facturas que superaron su fecha de vencimiento sin pago completo. Valores altos indican mayor riesgo de impago.",
            "pct_pagos_tardios": "Porcentaje de pagos realizados después de la fecha de vencimiento. Mide la consistencia en los tiempos de pago.",
            "dias_mora_promedio": "Promedio de días de retraso en los pagos. Valores más altos indican morosidad más severa.",
            "monto_promedio_factura": "Valor promedio de las facturas emitidas al cliente. Permite segmentar por tamaño de operación.",
            "cantidad_facturas": "Número total de facturas del cliente. Indica volumen de negocio y antigüedad de relación comercial.",
            "antiguedad_dias": "Antigüedad del cliente en días desde su primera factura. Clientes más antiguos pueden tener patrones de pago más estables."
        }

        # Summary KPIs in grid
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.container(border=True).metric("📊 Total Muestras", len(dataset_df))
        with col2:
            st.container(border=True).metric("✅ Bajo Riesgo", len(dataset_df[dataset_df['label'] == 0]))
        with col3:
            st.container(border=True).metric("⚠️ Alto Riesgo", len(dataset_df[dataset_df['label'] == 1]))
        with col4:
            balance = len(dataset_df[dataset_df['label'] == 1]) / len(dataset_df) * 100
            balance_color = "success" if 40 <= balance <= 60 else "warning" if 20 <= balance <= 80 else "danger"
            st.container(border=True).metric("⚖️ Balance", f"{balance:.1f}%")

        st.divider()

        # Distribution and Statistics in grid
        col1, col2 = st.columns(2)
        
        with col1:
            st.container(border=True).markdown("### 📈 Distribución de Clases")
            class_counts = dataset_df['label'].value_counts()
            fig = px.pie(values=class_counts.values, names=['Bajo Riesgo', 'Alto Riesgo'] if 0 in class_counts.index else ['Alto Riesgo'], hole=0.3)
            fig.update_layout(title="Balance de Clases", showlegend=True)
            st.plotly_chart(fig, use_container_width=True, key="class_distribution")
            
        with col2:
            st.container(border=True).markdown("### 📊 Estadísticas Descriptivas")
            st.dataframe(dataset_df.describe(), use_container_width=True)

        st.divider()

        # Feature Analysis with descriptions
        st.container(border=True).markdown("### 📉 Análisis de Features")
        
        feature_cols = ['pct_facturas_vencidas', 'pct_pagos_tardios', 'dias_mora_promedio',
                       'monto_promedio_factura', 'cantidad_facturas', 'antiguedad_dias']
        
        selected_feature = st.selectbox("Selecciona una feature para analizar:", feature_cols)
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.container(border=True).markdown(f"### 📊 {selected_feature}")
            st.markdown(f"<p class='feature-description'>{feature_descriptions[selected_feature]}</p>", unsafe_allow_html=True)
            
            fig = px.histogram(dataset_df, x=selected_feature, color='label', 
                             barmode='overlay', nbins=30,
                             title=f"Distribución de {selected_feature} por Clase")
            fig.update_layout(showlegend=True)
            st.plotly_chart(fig, use_container_width=True, key=f"feature_dist_{selected_feature}")
        
        with col2:
            st.container(border=True).markdown("### 📈 Estadísticas por Clase")
            stats_by_class = dataset_df.groupby('label')[selected_feature].describe()
            st.dataframe(stats_by_class, use_container_width=True)
            
            # Correlation with target
            correlation = dataset_df[[selected_feature, 'label']].corr().iloc[0, 1]
            st.metric(f"Correlación con Target", f"{correlation:.3f}")

        st.divider()

        # Boxplots comparison
        st.container(border=True).markdown("### 📦 Comparación de Features por Clase")
        
        # Create boxplot for all features
        fig_melt = px.box(dataset_df.melt(id_vars=['label'], value_vars=feature_cols), 
                         x='variable', y='value', color='label',
                         title="Distribución de Features por Clase de Riesgo")
        fig_melt.update_layout(xaxis_title="Feature", yaxis_title="Valor")
        st.plotly_chart(fig_melt, use_container_width=True, key="boxplot_comparison")

        st.divider()
        if st.button("Ir a Entrenamiento de Modelos →", type="primary", use_container_width=True):
            st.session_state.page = "🤖 Entrenamiento"
            st.rerun()

    elif page == "🤖 Entrenamiento":
        st.markdown("<h1 class='section-header'>Entrenamiento de Modelos</h1>", unsafe_allow_html=True)

        if 'dataset' not in st.session_state or st.session_state.dataset is None:
            st.warning("⚠️ Primero debes cargar los datos en la sección 'Cargar Datos'.")
            if st.button("Ir a Cargar Datos", use_container_width=True):
                st.session_state.page = "📁 Cargar Datos"
                st.rerun()
            return

        dataset = st.session_state.dataset

        # Dataset info in grid
        col1, col2, col3 = st.columns(3)
        with col1:
            st.container(border=True).metric("📊 Muestras", len(dataset))
        with col2:
            st.container(border=True).metric("📁 Fuente", st.session_state.data_source)
        with col3:
            st.container(border=True).metric("🔄 Tipo", "Incremental" if st.session_state.data_source == "Base de Datos" else "Inicial")

        st.divider()

        # Methodology panel (explicit and visible for documentation)
        st.container(border=True).markdown("""
        ### � Metodología de Entrenamiento
        
        **Validación Cruzada Estratificada (Stratified K-Fold):**
        - Divide el dataset en K folds manteniendo la proporción de clases en cada fold
        - Cada fold se usa una vez como validación y K-1 veces como entrenamiento
        - Proporciona estimación más robusta del rendimiento general del modelo
        - Número de folds: ajustado automáticamente según tamaño del dataset (mínimo 2, máximo 10)
        
        **Métricas de Evaluación:**
        - **F1-Score:** Media armónica de precision y recall (ideal para datasets desbalanceados)
        - **Accuracy:** Proporción de predicciones correctas
        - **Precision:** Proporción de positivos predichos que son realmente positivos
        - **Recall:** Proporción de positivos reales que fueron identificados correctamente
        - **ROC-AUC:** Área bajo la curva ROC (mide capacidad de discriminación)
        
        **Modelos Comparados:**
        1. **Logistic Regression:** Baseline interpretable con regularización
        2. **Random Forest:** Ensemble de árboles de decisión con bagging
        3. **Support Vector Machine:** Clasificador basado en márgenes máximos
        4. **Gradient Boosting:** Boosting secuencial de árboles débiles
        5. **Neural Network (MLP):** Perceptrón multicapa con backpropagation
        
        **Proceso de Selección:**
        - Se entrena cada modelo con validación cruzada
        - Se calculan métricas promedio y desviación estándar
        - Se selecciona el modelo con mejor F1-Score promedio
        - Se realizan tests estadísticos (t-test pareado) para validar significancia
        """)

        st.divider()

        # Training action
        if st.button("🚀 Entrenar y Comparar 5 Modelos", type="primary", use_container_width=True):
            with st.spinner("Entrenando y comparando modelos con cross-validation..."):
                result = compare_models(dataset)

                # Save best model for production (incremental if from DB)
                from app.ml.risk_model import train_model_with_type_incremental

                model_type_mapping = {
                    "Logistic Regression": "logistic",
                    "Random Forest": "random_forest",
                    "Support Vector Machine": "svm",
                    "Gradient Boosting": "gradient_boosting",
                    "Neural Network (MLP)": "mlp"
                }
                best_model_type = model_type_mapping.get(result.best_model, "logistic")

                if st.session_state.data_source == "Base de Datos":
                    train_model_with_type_incremental(dataset, best_model_type, use_saved=True)
                else:
                    train_model_with_type_incremental(dataset, best_model_type, use_saved=False)

                st.session_state.result = result
                st.success("✅ Entrenamiento completado exitosamente!")
                st.rerun()

        if 'result' in st.session_state:
            st.success("✅ Modelo entrenado. Ve a la sección 'Resultados' para ver el análisis completo.")
            if st.button("Ver Resultados →", type="secondary", use_container_width=True):
                st.session_state.page = "📋 Resultados"
                st.rerun()

    elif page == "📋 Resultados":
        st.markdown("<h1 class='section-header'>Resultados del Entrenamiento</h1>", unsafe_allow_html=True)

        if 'result' not in st.session_state:
            st.warning("⚠️ Primero debes entrenar los modelos en la sección 'Entrenamiento'.")
            if st.button("Ir a Entrenamiento", use_container_width=True):
                st.session_state.page = "🤖 Entrenamiento"
                st.rerun()
            return

        result = st.session_state.result
        dataset_size = st.session_state.dataset_size
        data_source = st.session_state.data_source
        dataset = st.session_state.dataset

        # Reduced to 4 tabs for better organization and capturability
        tab1, tab2, tab3, tab4 = st.tabs([
            "🏆 Mejor Modelo", "📊 Comparación", "🎯 Features", "🔍 Análisis Detallado"
        ])

        with tab1:
            # Complete hero view for article capture
            # Determine status color based on F1 score
            f1_status = result.best_f1
            if f1_status >= 0.8:
                status_color = "success"
                status_emoji = "✅"
                status_text = "Excelente"
            elif f1_status >= 0.7:
                status_color = "info"  
                status_emoji = "👍"
                status_text = "Bueno"
            elif f1_status >= 0.6:
                status_color = "warning"
                status_emoji = "⚠️"
                status_text = "Moderado"
            else:
                status_color = "error"
                status_emoji = "❌"
                status_text = "Necesita mejora"
            
            st.container(border=True).markdown(f"""
            ### 🏆 Modelo Ganador: {result.best_model}
            
            **Métricas Principales:**
            - **F1-Score:** {result.best_f1:.3f} (métrica principal de selección)
            - **Estado:** {status_emoji} {status_text}
            
            **Recomendación:**
            {result.recommendation}
            
            **Contexto del Entrenamiento:**
            - Dataset: {dataset_size} muestras desde {data_source}
            - Validación: Cross-validation estratificada
            - Modelos comparados: 5 algoritmos ML
            """)
            
            # Best model metrics in grid
            best_result = next(r for r in result.results if r.model_name == result.best_model)
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.container(border=True).metric("📊 F1-Score", f"{best_result.f1_mean:.3f}", f"±{best_result.f1_std:.3f}")
            with col2:
                st.container(border=True).metric("🎯 Accuracy", f"{best_result.accuracy_mean:.3f}", f"±{best_result.accuracy_std:.3f}")
            with col3:
                st.container(border=True).metric("💎 Precision", f"{best_result.precision_mean:.3f}", f"±{best_result.precision_std:.3f}")
            with col4:
                st.container(border=True).metric("🔍 Recall", f"{best_result.recall_mean:.3f}", f"±{best_result.recall_std:.3f}")

            st.divider()

            # PDF Export
            st.container(border=True).markdown("### 📄 Exportación de Reportes")
            if REPORTLAB_AVAILABLE:
                pdf_buffer = generate_pdf_report(result, dataset_size, data_source)
                if pdf_buffer:
                    st.download_button(
                        label="📄 Descargar Reporte PDF Completo",
                        data=pdf_buffer.getvalue(),
                        file_name=f"reporte_entrenamiento_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf",
                        mime="application/pdf",
                        type="primary",
                        use_container_width=True
                    )
            else:
                st.warning("Para descargar PDF, instala reportlab: pip install reportlab")

        with tab2:
            # Complete comparison view
            st.container(border=True).markdown("### 📊 Comparación de Modelos")
            
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

            st.divider()

            # Statistical tests
            if result.statistical_tests:
                st.container(border=True).markdown("### 🔬 Tests Estadísticos (t-test pareado)")
                tests_df = pd.DataFrame([
                    {
                        "Comparación": test,
                        "t-statistic": f"{data['t_statistic']:.3f}",
                        "p-value": f"{data['p_value']:.4f}",
                        "Significativo": "✅ Sí" if data['significant'] else "❌ No"
                    }
                    for test, data in result.statistical_tests.items()
                ])
                st.dataframe(tests_df, use_container_width=True)

            st.divider()

            # ROC Curves and Correlation in grid
            col1, col2 = st.columns(2)
            
            with col1:
                st.container(border=True).markdown("### 📈 Curvas ROC Comparativas")
                if result.roc_curves:
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
                    st.plotly_chart(fig, use_container_width=True, key="roc_curves")
            
            with col2:
                st.container(border=True).markdown("### 🔗 Matriz de Correlación")
                if result.correlation_matrix:
                    corr_df = pd.DataFrame(result.correlation_matrix)
                    fig = px.imshow(
                        corr_df,
                        text_auto=True,
                        aspect="auto",
                        color_continuous_scale='RdBu_r',
                        range_color=[-1, 1]
                    )
                    fig.update_layout(title="Correlación entre Features")
                    st.plotly_chart(fig, use_container_width=True, key="correlation_heatmap")

        with tab3:
            # Feature analysis view
            st.container(border=True).markdown("### 🎯 Comparación de Feature Importance")
            
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
            st.plotly_chart(fig, use_container_width=True, key="feature_importance_comparison")

            st.divider()

            # Cross-validation details
            st.container(border=True).markdown("### 🔄 Detalles de Cross-Validation")
            st.info("Configuración: Stratified K-Fold con n_splits ajustado dinámicamente según tamaño de dataset")

            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("#### Scores por Fold")
                fold_data = []
                for result_item in result.results:
                    for i, score in enumerate(result_item.f1_scores):
                        fold_data.append({
                            "Modelo": result_item.model_name,
                            "Fold": i + 1,
                            "F1-Score": score
                        })

                fold_df = pd.DataFrame(fold_data)
                fig = px.line(fold_df, x="Fold", y="F1-Score", color="Modelo", markers=True)
                fig.update_layout(title="F1-Score por Fold", yaxis_title="F1-Score")
                st.plotly_chart(fig, use_container_width=True, key="fold_scores")
            
            with col2:
                st.markdown("#### Análisis de Varianza")
                variance_data = []
                for result_item in result.results:
                    variance_data.append({
                        "Modelo": result_item.model_name,
                        "Varianza F1": result_item.f1_std ** 2,
                        "Estabilidad": "Alta" if result_item.f1_std < 0.05 else "Media" if result_item.f1_std < 0.1 else "Baja"
                    })

                variance_df = pd.DataFrame(variance_data)
                st.dataframe(variance_df, use_container_width=True)

        with tab4:
            # Detailed analysis view
            st.container(border=True).markdown("### 🔍 Detalles Individuales por Modelo")
            
            for result_item in result.results:
                with st.expander(f"📊 {result_item.model_name} - F1: {result_item.f1_mean:.3f}"):
                    col1, col2 = st.columns(2)

                    with col1:
                        st.markdown("#### Hiperparámetros")
                        if result_item.hyperparameters:
                            key_params = {}
                            for param, value in result_item.hyperparameters.items():
                                if param in ['n_estimators', 'max_depth', 'learning_rate', 'C', 'kernel', 'hidden_layer_sizes', 'alpha']:
                                    key_params[param] = value
                            st.json(key_params if key_params else result_item.hyperparameters)
                        else:
                            st.info("No hay hiperparámetros disponibles")

                    with col2:
                        st.markdown("#### Matriz de Confusión")
                        if result_item.confusion_matrix:
                            cm = np.array(result_item.confusion_matrix)
                            fig = px.imshow(cm, text_auto=True, aspect="auto",
                                          color_continuous_scale='Blues',
                                          labels=dict(x="Predicho", y="Real", color="Count"))
                            fig.update_layout(title="Matriz de Confusión")
                            st.plotly_chart(fig, use_container_width=True, key=f"confusion_matrix_{result_item.model_name.replace(' ', '_')}")
                        else:
                            st.info("Matriz de confusión no disponible")

                    st.markdown("#### Performance Detallada")
                    perf_data = {
                        "Métrica": ["F1-Score", "Accuracy", "Precision", "Recall", "ROC-AUC", "Tiempo Entrenamiento"],
                        "Valor": [
                            f"{result_item.f1_mean:.3f} ± {result_item.f1_std:.3f}",
                            f"{result_item.accuracy_mean:.3f} ± {result_item.accuracy_std:.3f}",
                            f"{result_item.precision_mean:.3f} ± {result_item.precision_std:.3f}",
                            f"{result_item.recall_mean:.3f} ± {result_item.recall_std:.3f}",
                            f"{result_item.roc_auc_mean:.3f} ± {result_item.roc_auc_std:.3f}",
                            f"{result_item.training_time:.2f}s"
                        ]
                    }
                    st.dataframe(pd.DataFrame(perf_data), use_container_width=True)

            st.divider()

            # Error analysis
            st.container(border=True).markdown("### ⚠️ Análisis de Errores")
            st.info("ℹ️ Este análisis usa predicciones out-of-fold del cross-validation para estimación realista del error.")
            
            X = np.array([features_to_vector(f) for f in dataset])
            y = np.array([f.label for f in dataset])

            # Use out-of-fold predictions if available
            if result.out_of_fold_predictions and result.best_model in result.out_of_fold_predictions:
                y_pred = result.out_of_fold_predictions[result.best_model]
                st.success("✅ Usando predicciones out-of-fold del cross-validation")
            else:
                # Fallback to in-sample predictions
                st.warning("⚠️ Predicciones out-of-fold no disponibles, usando predicciones in-sample")
                from app.ml.risk_model import _build_pipeline
                model_type_mapping = {
                    "Logistic Regression": "logistic",
                    "Random Forest": "random_forest",
                    "Support Vector Machine": "svm",
                    "Gradient Boosting": "gradient_boosting",
                    "Neural Network (MLP)": "mlp"
                }
                best_model_type = model_type_mapping.get(result.best_model, "logistic")
                pipeline = _build_pipeline(best_model_type)
                pipeline.fit(X, y)
                y_pred = pipeline.predict(X)

            misclassified = []
            for i, (true_label, pred_label) in enumerate(zip(y, y_pred)):
                if true_label != pred_label:
                    misclassified.append({
                        "Índice": i,
                        "Real": "Alto Riesgo" if true_label == 1 else "Bajo Riesgo",
                        "Predicho": "Alto Riesgo" if pred_label == 1 else "Bajo Riesgo",
                        "pct_facturas_vencidas": dataset[i].pct_facturas_vencidas,
                        "pct_pagos_tardios": dataset[i].pct_pagos_tardios,
                        "dias_mora_promedio": dataset[i].dias_mora_promedio
                    })

            if misclassified:
                st.markdown(f"#### Casos Mal Clasificados ({len(misclassified)} de {len(dataset)})")
                st.dataframe(pd.DataFrame(misclassified), use_container_width=True)
            else:
                st.success("✅ No hay errores de clasificación en el dataset")

            st.divider()

            # Performance summary
            st.container(border=True).markdown("### 📊 Resumen de Performance de Todos los Modelos")
            perf_summary_data = []
            for result_item in result.results:
                perf_summary_data.append({
                    "Modelo": result_item.model_name,
                    "F1-Score": f"{result_item.f1_mean:.3f} ± {result_item.f1_std:.3f}",
                    "Accuracy": f"{result_item.accuracy_mean:.3f} ± {result_item.accuracy_std:.3f}",
                    "Precision": f"{result_item.precision_mean:.3f} ± {result_item.precision_std:.3f}",
                    "Recall": f"{result_item.recall_mean:.3f} ± {result_item.recall_std:.3f}",
                    "ROC-AUC": f"{result_item.roc_auc_mean:.3f} ± {result_item.roc_auc_std:.3f}",
                    "Tiempo (s)": f"{result_item.training_time:.2f}"
                })
            st.dataframe(pd.DataFrame(perf_summary_data), use_container_width=True)


        st.divider()

        if st.button("🔄 Reentrenar Modelos", type="secondary", use_container_width=True):
            del st.session_state.result
            st.rerun()

if __name__ == "__main__":
    main()

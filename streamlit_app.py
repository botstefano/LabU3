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
    # Convert to SQLAlchemy-like objects
    from app.models.client import Client
    from app.models.invoice import Invoice
    from app.models.payment import Payment

    dataset = []

    for _, client in clients_df.iterrows():
        client_invoices = invoices_df[invoices_df['client_id'] == client['id']]

        payments_by_invoice = {}
        for _, inv in client_invoices.iterrows():
            invoice_payments = payments_df[payments_df['invoice_id'] == inv['id']]
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
            payments_by_invoice[str(inv['id'])] = payment_objs
        
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
    .main-header {
        font-size: 2.5rem;
        font-weight: 700;
        color: #1e88e5;
        margin-bottom: 0.5rem;
    }
    .sub-header {
        font-size: 1.2rem;
        color: #666;
        margin-bottom: 2rem;
    }
    .section-header {
        font-size: 1.8rem;
        font-weight: 600;
        color: #333;
        margin-top: 2rem;
        margin-bottom: 1rem;
        border-bottom: 2px solid #1e88e5;
        padding-bottom: 0.5rem;
    }
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1rem;
        border-radius: 10px;
        color: white;
        margin: 0.5rem 0;
    }
    .stDataFrame {
        margin-top: 1rem;
        margin-bottom: 1rem;
    }
    div[data-testid="stVerticalBlock"] > div[style*="flex-direction: column"] > div > div > div {
        margin-bottom: 1rem;
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

        st.divider()

        col1, col2, col3 = st.columns(3)

        with col1:
            st.metric("Modelos Disponibles", "5", "Logistic, RF, SVM, GB, MLP")
            st.info("📊 Comparación de múltiples algoritmos")

        with col2:
            st.metric("Features", "6", "Características de clientes")
            st.info("🔍 Análisis detallado de variables")

        with col3:
            st.metric("Exportación", "PDF", "Reportes profesionales")
            st.info("📄 Documentación completa")

        st.divider()

        st.markdown("### 🚀 Características Principales")

        col1, col2 = st.columns(2)

        with col1:
            st.markdown("""
            **📁 Gestión de Datos**
            - Carga de datasets CSV
            - Entrenamiento incremental desde BD
            - Análisis exploratorio de datos
            """)

        with col2:
            st.markdown("""
            **🤖 Modelos ML**
            - Logistic Regression
            - Random Forest
            - Support Vector Machine
            - Gradient Boosting
            - Neural Network (MLP)
            """)

        st.divider()

        st.markdown("### 📊 Flujo de Trabajo")

        st.markdown("""
        1. **Cargar Datos:** Selecciona fuente de datos (CSV o BD)
        2. **Análisis Dataset:** Explora estadísticas y distribuciones
        3. **Entrenamiento:** Compara 5 modelos con cross-validation
        4. **Resultados:** Analiza métricas y exporta reportes
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
                            continue

                    st.success(f"✅ Dataset cargado desde CSV: {len(dataset)} muestras")
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
            st.warning("⚠️ Primero debes cargar los en la sección 'Cargar Datos'.")
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

        # Tabs for different analysis views
        tab1, tab2, tab3, tab4 = st.tabs(["📊 Resumen", "📈 Distribución", "📉 Features", "📦 Boxplots"])

        with tab1:
            st.markdown("### 📊 Resumen de Datos")
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Total Muestras", len(dataset_df))
            with col2:
                st.metric("Bajo Riesgo", len(dataset_df[dataset_df['label'] == 0]))
            with col3:
                st.metric("Alto Riesgo", len(dataset_df[dataset_df['label'] == 1]))
            with col4:
                balance = len(dataset_df[dataset_df['label'] == 1]) / len(dataset_df) * 100
                st.metric("Balance", f"{balance:.1f}%")

        with tab2:
            st.markdown("### 📈 Distribución y Estadísticas")
            col1, col2 = st.columns(2)
            with col1:
                st.markdown("#### Distribución de Clases")
                class_counts = dataset_df['label'].value_counts()
                fig = px.pie(values=class_counts.values, names=['Bajo Riesgo', 'Alto Riesgo'] if 0 in class_counts.index else ['Alto Riesgo'], hole=0.3)
                fig.update_layout(title="Balance de Clases")
                st.plotly_chart(fig, use_container_width=True, key="class_distribution")

            with col2:
                st.markdown("#### Estadísticas Descriptivas")
                st.dataframe(dataset_df.describe(), use_container_width=True)

        with tab3:
            st.markdown("### 📉 Análisis de Features")
            feature_cols = ['pct_facturas_vencidas', 'pct_pagos_tardios', 'dias_mora_promedio',
                           'monto_promedio_factura', 'cantidad_facturas', 'antiguedad_dias']

            selected_feature = st.selectbox("Selecciona feature para visualizar", feature_cols)

            fig = px.histogram(dataset_df, x=selected_feature, color='label',
                              barmode='overlay', nbins=20,
                              title=f"Distribución de {selected_feature} por Clase")
            st.plotly_chart(fig, use_container_width=True, key="feature_distribution")

        with tab4:
            st.markdown("### 📦 Boxplots Comparativos")
            feature_cols = ['pct_facturas_vencidas', 'pct_pagos_tardios', 'dias_mora_promedio',
                           'monto_promedio_factura', 'cantidad_facturas', 'antiguedad_dias']

            fig = go.Figure()
            for i, feature in enumerate(feature_cols):
                fig.add_trace(go.Box(
                    y=dataset_df[dataset_df['label'] == 0][feature],
                    name=f'{feature} (Bajo)',
                    marker_color='blue'
                ))
                fig.add_trace(go.Box(
                    y=dataset_df[dataset_df['label'] == 1][feature],
                    name=f'{feature} (Alto)',
                    marker_color='red'
                ))

            fig.update_layout(title="Distribución de Features por Clase", yaxis_title="Valor", height=600)
            st.plotly_chart(fig, use_container_width=True, key="boxplot_comparison")

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

        st.info(f"📊 Dataset cargado: {len(dataset)} muestras desdefuente: {st.session_state.data_source}")

        st.divider()

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

        # Tabs for different result views
        tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
            "🏆 Mejor Modelo", "📊 Comparación", "📈 Curvas ROC", 
            "🎯 Features", "🔍 Detalles", "⚠️ Errores", "📊 Performance"
        ])

        with tab1:
            st.markdown("### 🏆 Mejor Modelo")
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Modelo Seleccionado", result.best_model)
            with col2:
                st.metric("F1-Score", f"{result.best_f1:.3f}")
            with col3:
                status = "Excelente" if result.best_f1 >= 0.9 else "Bueno" if result.best_f1 >= 0.8 else "Moderado"
                st.metric("Estado", status)

            st.info(f"💡 {result.recommendation}")

            st.divider()

            st.markdown("### 📄 Exportación de Reportes")
            if REPORTLAB_AVAILABLE:
                pdf_buffer = generate_pdf_report(result, dataset_size, data_source)
                if pdf_buffer:
                    st.download_button(
                        label="📄 Descargar Reporte PDF",
                        data=pdf_buffer.getvalue(),
                        file_name=f"reporte_entrenamiento_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf",
                        mime="application/pdf",
                        type="primary",
                        use_container_width=True
                    )
            else:
                st.warning("Para descargar PDF, instala reportlab: pip install reportlab")

        with tab2:
            st.markdown("### 📊 Comparación de Modelos")
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

            if result.statistical_tests:
                st.markdown("### 🔬 Tests Estadísticos (t-test pareado)")
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

        with tab3:
            if result.correlation_matrix:
                st.markdown("### 🔗 Matriz de Correlación de Features")
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

            st.divider()

            if result.roc_curves:
                st.markdown("### 📈 Curvas ROC Comparativas")
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

        with tab4:
            st.markdown("### 🎯 Comparación de Feature Importance")
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

            st.markdown("### 🔄 Detalles de Cross-Validation")
            st.info(f"Configuración: Stratified K-Fold con n_splits ajustado dinámicamente según tamaño de dataset")

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

            st.markdown("#### Análisis de Varianza entre Folds")
            variance_data = []
            for result_item in result.results:
                variance_data.append({
                    "Modelo": result_item.model_name,
                    "Varianza F1": result_item.f1_std ** 2,
                    "Estabilidad": "Alta" if result_item.f1_std < 0.05 else "Media" if result_item.f1_std < 0.1 else "Baja"
                })

            variance_df = pd.DataFrame(variance_data)
            st.dataframe(variance_df, use_container_width=True)

        with tab5:
            st.markdown("### 🔍 Detalles Individuales por Modelo")
            for result_item in result.results:
                with st.expander(f"📊 {result_item.model_name}"):
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

        with tab6:
            st.markdown("### ⚠️ Análisis de Errores")
            from app.ml.risk_model import _build_pipeline
            X = np.array([features_to_vector(f) for f in dataset])
            y = np.array([f.label for f in dataset])

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
                st.warning(f"⚠️ Se encontraron {len(misclassified)} casos mal clasificados")
                misclassified_df = pd.DataFrame(misclassified)
                st.dataframe(misclassified_df, use_container_width=True)
            else:
                st.success("✅ No hay casos mal clasificados en el dataset de entrenamiento")

            st.divider()

            st.markdown("#### Distribución de Probabilidades Predichas")
            if hasattr(pipeline.named_steps['classifier'], 'predict_proba'):
                y_proba = pipeline.predict_proba(X)[:, 1]
                fig = px.histogram(x=y_proba, color=y, nbins=30,
                                 title="Distribución de Probabilidades de Alto Riesgo",
                                 labels={"x": "Probabilidad", "color": "Clase Real"})
                fig.update_layout(barmode='overlay')
                st.plotly_chart(fig, use_container_width=True, key="probability_distribution")

                st.markdown("#### Análisis de Threshold")
                thresholds = np.arange(0.1, 0.9, 0.1)
                threshold_results = []

                for threshold in thresholds:
                    y_pred_thresh = (y_proba >= threshold).astype(int)
                    f1 = f1_score(y, y_pred_thresh, zero_division=0)
                    precision = precision_score(y, y_pred_thresh, zero_division=0)
                    recall = recall_score(y, y_pred_thresh, zero_division=0)
                    threshold_results.append({
                        "Threshold": threshold,
                        "F1": f1,
                        "Precision": precision,
                        "Recall": recall
                    })

                threshold_df = pd.DataFrame(threshold_results)
                fig = px.line(threshold_df, x="Threshold", y=["F1", "Precision", "Recall"],
                             markers=True, title="Métricas vs Threshold")
                st.plotly_chart(fig, use_container_width=True, key="threshold_analysis")
            else:
                st.info("El modelo seleccionado no soporta predict_proba")

        with tab7:
            st.markdown("### 📊 Resumen de Performance")
            perf_summary = []
            for result_item in result.results:
                perf_summary.append({
                    "Modelo": result_item.model_name,
                    "Tiempo Entrenamiento (s)": result_item.training_time,
                    "Tiempo por Fold (s)": result_item.training_time / len(result_item.f1_scores),
                    "Estabilidad CV": "Alta" if result_item.f1_std < 0.05 else "Media" if result_item.f1_std < 0.1 else "Baja"
                })

            perf_summary_df = pd.DataFrame(perf_summary)
            st.dataframe(perf_summary_df, use_container_width=True)

        st.divider()

        if st.button("🔄 Reentrenar Modelos", type="secondary", use_container_width=True):
            del st.session_state.result
            st.rerun()

if __name__ == "__main__":
    main()

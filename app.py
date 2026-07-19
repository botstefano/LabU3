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

# ---------------------------------------------------------------------------
# Descripciones de negocio para features y modelos.
# Se muestran en la UI para que cada pantalla sea autocontenida y explicativa
# (útil tanto para el usuario final como para tomar capturas para el artículo).
# ---------------------------------------------------------------------------
FEATURE_DESCRIPTIONS = {
    "pct_facturas_vencidas": "Porcentaje de facturas del cliente que superaron su fecha de vencimiento sin haber sido pagadas.",
    "pct_pagos_tardios": "Porcentaje de pagos que el cliente realizó después de la fecha acordada.",
    "dias_mora_promedio": "Promedio de días de retraso en los pagos del cliente (mora).",
    "monto_promedio_factura": "Monto promedio facturado al cliente por cada factura emitida.",
    "cantidad_facturas": "Número total de facturas emitidas al cliente hasta la fecha.",
    "antiguedad_dias": "Antigüedad del cliente en días, desde su fecha de registro.",
}

MODEL_TYPE_MAPPING = {
    "Logistic Regression": "logistic",
    "Random Forest": "random_forest",
    "Support Vector Machine": "svm",
    "Gradient Boosting": "gradient_boosting",
    "Neural Network (MLP)": "mlp",
}

NAV_ITEMS = [
    ("home", "Inicio"),
    ("load", "Cargar datos"),
    ("analysis", "Análisis dataset"),
    ("train", "Entrenamiento"),
    ("results", "Resultados"),
]

# Page config
st.set_page_config(
    page_title="ML Risk Scoring",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded"
)


# ---------------------------------------------------------------------------
# Datos y features (sin cambios de lógica respecto a la versión original)
# ---------------------------------------------------------------------------
@st.cache_resource
def get_db_engine():
    from app.core.config import get_settings
    settings = get_settings()
    return create_engine(settings.database_url)


def load_data():
    """Load data from database"""
    engine = get_db_engine()
    clients_df = pd.read_sql("SELECT * FROM clients", engine)
    invoices_df = pd.read_sql("SELECT * FROM invoices", engine)
    payments_df = pd.read_sql("SELECT * FROM payments", engine)
    return clients_df, invoices_df, payments_df


def compute_features_from_db(clients_df, invoices_df, payments_df):
    """Compute features from database data"""
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

    title_style = ParagraphStyle(
        'CustomTitle', parent=styles['Heading1'], fontSize=18,
        textColor=colors.HexColor('#1e88e5'), alignment=TA_CENTER, spaceAfter=30
    )
    heading_style = ParagraphStyle(
        'CustomHeading', parent=styles['Heading2'], fontSize=14,
        textColor=colors.HexColor('#333333'), spaceAfter=12
    )

    content = []
    content.append(Paragraph("Reporte de Entrenamiento de Modelos ML", title_style))
    content.append(Spacer(1, 12))
    content.append(Paragraph(f"<b>Fecha:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", styles['Normal']))
    content.append(Paragraph(f"<b>Fuente de datos:</b> {data_source}", styles['Normal']))
    content.append(Paragraph(f"<b>Tamaño del dataset:</b> {dataset_size} muestras", styles['Normal']))
    content.append(Spacer(1, 12))

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

    content.append(Paragraph("Recomendación", heading_style))
    content.append(Paragraph(result.recommendation, styles['Normal']))
    content.append(Spacer(1, 12))

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

    doc.build(content)
    buffer.seek(0)
    return buffer


# ---------------------------------------------------------------------------
# Estilos: variables CSS + soporte de dark mode + tarjetas reutilizables
# ---------------------------------------------------------------------------
def inject_css():
    st.markdown("""
    <style>
    :root {
        --app-primary: #1e88e5;
        --app-primary-dark: #0c447c;
        --app-success-bg: #e6f4ea;
        --app-success-text: #1e7e34;
        --app-warning-bg: #fff4e5;
        --app-warning-text: #a05a00;
        --app-danger-bg: #fdecea;
        --app-danger-text: #a32d2d;
        --app-card-bg: #f6f8fb;
        --app-text-secondary: #5f6368;
        --app-border: rgba(0,0,0,0.08);
    }
    @media (prefers-color-scheme: dark) {
        :root {
            --app-primary: #4fa3ea;
            --app-primary-dark: #85b7eb;
            --app-success-bg: rgba(30,126,52,0.18);
            --app-success-text: #6fcf87;
            --app-warning-bg: rgba(160,90,0,0.18);
            --app-warning-text: #f0b45a;
            --app-danger-bg: rgba(163,45,45,0.2);
            --app-danger-text: #f09595;
            --app-card-bg: rgba(255,255,255,0.05);
            --app-text-secondary: #b0b3b8;
            --app-border: rgba(255,255,255,0.12);
        }
    }

    .main-header {
        font-size: 2.2rem;
        font-weight: 700;
        color: var(--app-primary);
        margin-bottom: 0.25rem;
    }
    .sub-header {
        font-size: 1.05rem;
        color: var(--app-text-secondary);
        margin-bottom: 1.25rem;
    }
    .section-header {
        font-size: 1.6rem;
        font-weight: 600;
        margin-top: 0.5rem;
        margin-bottom: 1rem;
        border-bottom: 2px solid var(--app-primary);
        padding-bottom: 0.5rem;
    }
    .metric-card {
        background: var(--app-card-bg);
        border: 1px solid var(--app-border);
        border-radius: 10px;
        padding: 1rem 1.1rem;
        margin: 0 0 0.5rem 0;
    }
    .metric-card .label {
        font-size: 0.8rem;
        color: var(--app-text-secondary);
        margin-bottom: 0.2rem;
    }
    .metric-card .value {
        font-size: 1.6rem;
        font-weight: 700;
    }
    .metric-card .hint {
        font-size: 0.78rem;
        color: var(--app-text-secondary);
        margin-top: 0.2rem;
    }
    .status-pill {
        display: inline-block;
        padding: 0.25rem 0.7rem;
        border-radius: 999px;
        font-size: 0.85rem;
        font-weight: 600;
    }
    .status-good { background: var(--app-success-bg); color: var(--app-success-text); }
    .status-warn { background: var(--app-warning-bg); color: var(--app-warning-text); }
    .status-bad  { background: var(--app-danger-bg); color: var(--app-danger-text); }

    .info-card {
        background: var(--app-card-bg);
        border: 1px solid var(--app-border);
        border-radius: 10px;
        padding: 1rem 1.2rem;
        margin-bottom: 0.75rem;
    }
    .feature-desc {
        font-size: 0.85rem;
        color: var(--app-text-secondary);
        margin-top: -0.4rem;
        margin-bottom: 0.6rem;
    }
    </style>
    """, unsafe_allow_html=True)


def metric_card(label, value, hint=None):
    hint_html = f"<div class='hint'>{hint}</div>" if hint else ""
    st.markdown(
        f"""<div class="metric-card">
                <div class="label">{label}</div>
                <div class="value">{value}</div>
                {hint_html}
            </div>""",
        unsafe_allow_html=True
    )


def status_pill(text, kind="good"):
    css_class = {"good": "status-good", "warn": "status-warn", "bad": "status-bad"}.get(kind, "status-good")
    st.markdown(f'<span class="status-pill {css_class}">{text}</span>', unsafe_allow_html=True)


def f1_status(f1):
    if f1 >= 0.85:
        return "Excelente", "good"
    if f1 >= 0.7:
        return "Bueno", "warn"
    return "Moderado", "bad"


# ---------------------------------------------------------------------------
# Páginas
# ---------------------------------------------------------------------------
def render_sidebar():
    with st.sidebar:
        st.markdown("""
        <div style='text-align: center; padding: 12px 0 4px;'>
            <h1 style='color: var(--app-primary); font-size: 1.6rem; font-weight: 700; margin-bottom:2px;'>🧠 ML Risk Scoring</h1>
            <p style='color: var(--app-text-secondary); font-size: 0.85rem;'>Sistema de evaluación de riesgo</p>
        </div>
        """, unsafe_allow_html=True)
        st.divider()

        labels = [label for _, label in NAV_ITEMS]
        keys = [key for key, _ in NAV_ITEMS]

        if 'page_key' not in st.session_state:
            st.session_state.page_key = "home"

        selected_label = st.radio(
            "Selecciona una sección:",
            labels,
            index=keys.index(st.session_state.page_key),
            label_visibility="collapsed",
        )
        st.session_state.page_key = keys[labels.index(selected_label)]

        st.divider()
        with st.expander("ℹ️ Información del sistema"):
            st.markdown("""
            **Versión:** 1.0.0
            **Estado:** Producción
            **Última actualización:** 2026-07-18

            Compara 5 modelos ML para scoring de riesgo de morosidad,
            con entrenamiento incremental y exportación de reportes.
            """)

        return st.session_state.page_key


def go_to(page_key):
    st.session_state.page_key = page_key
    st.rerun()


def page_home():
    st.markdown("<h1 class='main-header'>ML Risk Scoring</h1>", unsafe_allow_html=True)
    st.markdown(
        "<p class='sub-header'>Sistema de comparación de modelos de machine learning "
        "para scoring de riesgo de morosidad de clientes.</p>",
        unsafe_allow_html=True
    )

    col1, col2, col3 = st.columns(3)
    with col1:
        metric_card("Modelos comparados", "5", "Logistic · RF · SVM · GB · MLP")
    with col2:
        metric_card("Features utilizadas", "6", "Comportamiento de pago del cliente")
    with col3:
        if 'result' in st.session_state:
            metric_card("Último F1-score", f"{st.session_state.result.best_f1:.3f}",
                        st.session_state.result.best_model)
        else:
            metric_card("Último F1-score", "—", "Aún no se ha entrenado un modelo")

    st.divider()

    left, right = st.columns([1.1, 1])
    with left:
        st.markdown("#### 🚀 Qué resuelve este sistema")
        st.markdown("""
        <div class="info-card">
        La cobranza reactiva es costosa: identificar con anticipación qué clientes
        tienen alta probabilidad de caer en mora permite priorizar seguimiento y
        ajustar condiciones de crédito antes de que ocurra el impago. Este sistema
        entrena y compara 5 algoritmos de clasificación sobre el historial de pagos
        de cada cliente, y selecciona automáticamente el de mejor desempeño.
        </div>
        """, unsafe_allow_html=True)

        st.markdown("#### 📊 Flujo de trabajo")
        steps = st.columns(4)
        step_labels = ["1. Cargar datos", "2. Analizar dataset", "3. Entrenar modelos", "4. Ver resultados"]
        for col, label in zip(steps, step_labels):
            with col:
                st.markdown(f"<div class='info-card' style='text-align:center; font-size:0.85rem;'>{label}</div>",
                            unsafe_allow_html=True)

    with right:
        st.markdown("#### 🤖 Modelos disponibles")
        st.markdown("""
        <div class="info-card">
        <b>Logistic Regression</b> — baseline lineal e interpretable<br>
        <b>Random Forest</b> — ensamble robusto a outliers<br>
        <b>Support Vector Machine</b> — bueno en fronteras no lineales<br>
        <b>Gradient Boosting</b> — alto desempeño en tabular data<br>
        <b>Neural Network (MLP)</b> — captura interacciones complejas
        </div>
        """, unsafe_allow_html=True)

        st.markdown("#### 📐 Metodología")
        st.markdown("""
        <div class="info-card">
        Validación cruzada estratificada (Stratified K-Fold) con número de folds
        ajustado al tamaño del dataset, comparación con tests estadísticos
        pareados (t-test), y selección automática por F1-score.
        </div>
        """, unsafe_allow_html=True)

    st.divider()
    if st.button("Comenzar →", type="primary", use_container_width=True):
        go_to("load")


def page_load():
    st.markdown("<h1 class='section-header'>Carga de datos</h1>", unsafe_allow_html=True)

    col_csv, col_db = st.columns(2)
    with col_csv:
        st.markdown("""
        <div class="info-card">
        <b>📄 Archivo CSV</b><br>
        <span style="font-size:0.85rem; color:var(--app-text-secondary);">
        Para el primer entrenamiento, cuando aún no hay historial en la base de datos.
        </span>
        </div>
        """, unsafe_allow_html=True)
    with col_db:
        st.markdown("""
        <div class="info-card">
        <b>📊 Base de datos</b><br>
        <span style="font-size:0.85rem; color:var(--app-text-secondary);">
        Entrenamiento incremental usando el historial real de clientes, facturas y pagos.
        </span>
        </div>
        """, unsafe_allow_html=True)

    data_source = st.radio(
        "Selecciona la fuente de datos para el entrenamiento:",
        ["📄 Archivo CSV (Primer entrenamiento)", "📊 Base de Datos (Incremental)"],
        horizontal=True,
    )

    dataset = None

    if data_source == "📄 Archivo CSV (Primer entrenamiento)":
        uploaded_file = st.file_uploader("Cargar archivo CSV con dataset inicial", type=['csv'])

        if uploaded_file:
            try:
                from app.ml.features import ClientFeatures

                df = pd.read_csv(uploaded_file)
                dataset = []
                skipped = 0

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
                        skipped += 1
                        continue

                if skipped:
                    st.warning(f"⚠️ Se omitieron {skipped} filas inválidas de {len(df)} totales.")

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
        if st.button("Ir a análisis de dataset →", type="primary", use_container_width=True):
            go_to("analysis")


def page_analysis():
    st.markdown("<h1 class='section-header'>Análisis del dataset</h1>", unsafe_allow_html=True)

    if 'dataset' not in st.session_state or st.session_state.dataset is None:
        st.warning("⚠️ Primero debes cargar los datos en la sección 'Cargar datos'.")
        if st.button("Ir a cargar datos", use_container_width=True):
            go_to("load")
        return

    dataset = st.session_state.dataset

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

    # KPIs siempre visibles arriba, sin necesidad de scroll
    total = len(dataset_df)
    bajo_riesgo = len(dataset_df[dataset_df['label'] == 0])
    alto_riesgo = len(dataset_df[dataset_df['label'] == 1])
    balance = (alto_riesgo / total * 100) if total else 0

    kpi1, kpi2, kpi3, kpi4 = st.columns(4)
    with kpi1:
        metric_card("Total muestras", total)
    with kpi2:
        metric_card("Bajo riesgo", bajo_riesgo)
    with kpi3:
        metric_card("Alto riesgo", alto_riesgo)
    with kpi4:
        metric_card("Balance de clases", f"{balance:.1f}%")
        if balance < 15 or balance > 85:
            status_pill("Desbalanceado", "warn")
        else:
            status_pill("Balanceado", "good")

    st.divider()

    tab1, tab2, tab3 = st.tabs(["📈 Distribución", "📉 Features", "📦 Boxplots"])

    with tab1:
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("#### Distribución de clases")
            class_counts = dataset_df['label'].value_counts()
            fig = px.pie(
                values=class_counts.values,
                names=['Bajo Riesgo', 'Alto Riesgo'] if 0 in class_counts.index else ['Alto Riesgo'],
                hole=0.3
            )
            fig.update_layout(margin=dict(t=10, b=10, l=10, r=10), height=320)
            st.plotly_chart(fig, use_container_width=True, key="class_distribution")
        with col2:
            st.markdown("#### Estadísticas descriptivas")
            st.dataframe(dataset_df.describe(), use_container_width=True, height=320)

    with tab2:
        feature_cols = ['pct_facturas_vencidas', 'pct_pagos_tardios', 'dias_mora_promedio',
                        'monto_promedio_factura', 'cantidad_facturas', 'antiguedad_dias']

        col_select, col_chart = st.columns([1, 2])
        with col_select:
            selected_feature = st.selectbox("Selecciona feature para visualizar", feature_cols)
            st.markdown(
                f"<div class='feature-desc'>{FEATURE_DESCRIPTIONS.get(selected_feature, '')}</div>",
                unsafe_allow_html=True
            )
            with st.expander("Ver descripción de todas las features"):
                for feat, desc in FEATURE_DESCRIPTIONS.items():
                    st.markdown(f"**{feat}**: {desc}")

        with col_chart:
            fig = px.histogram(dataset_df, x=selected_feature, color='label',
                              barmode='overlay', nbins=20)
            fig.update_layout(margin=dict(t=10, b=10, l=10, r=10), height=340)
            st.plotly_chart(fig, use_container_width=True, key="feature_distribution")

    with tab3:
        feature_cols = ['pct_facturas_vencidas', 'pct_pagos_tardios', 'dias_mora_promedio',
                        'monto_promedio_factura', 'cantidad_facturas', 'antiguedad_dias']

        fig = go.Figure()
        for feature in feature_cols:
            fig.add_trace(go.Box(
                y=dataset_df[dataset_df['label'] == 0][feature],
                name=f'{feature} (Bajo)',
                marker_color='#1e88e5'
            ))
            fig.add_trace(go.Box(
                y=dataset_df[dataset_df['label'] == 1][feature],
                name=f'{feature} (Alto)',
                marker_color='#e24b4a'
            ))

        fig.update_layout(yaxis_title="Valor", height=480, margin=dict(t=10, b=10, l=10, r=10))
        st.plotly_chart(fig, use_container_width=True, key="boxplot_comparison")

    st.divider()
    if st.button("Ir a entrenamiento de modelos →", type="primary", use_container_width=True):
        go_to("train")


def page_train():
    st.markdown("<h1 class='section-header'>Entrenamiento de modelos</h1>", unsafe_allow_html=True)

    if 'dataset' not in st.session_state or st.session_state.dataset is None:
        st.warning("⚠️ Primero debes cargar los datos en la sección 'Cargar datos'.")
        if st.button("Ir a cargar datos", use_container_width=True):
            go_to("load")
        return

    dataset = st.session_state.dataset

    col_info, col_meth = st.columns([1, 1])
    with col_info:
        metric_card("Dataset cargado", f"{len(dataset)} muestras", f"Fuente: {st.session_state.data_source}")
    with col_meth:
        st.markdown("""
        <div class="info-card">
        <b>📐 Metodología de validación</b><br>
        <span style="font-size:0.85rem; color:var(--app-text-secondary);">
        Stratified K-Fold cross-validation (folds ajustados al tamaño del dataset).
        Métricas calculadas: F1-score, accuracy, precision, recall y ROC-AUC.
        Comparación entre modelos con t-test pareado.
        </span>
        </div>
        """, unsafe_allow_html=True)

    st.divider()

    if st.button("🚀 Entrenar y comparar 5 modelos", type="primary", use_container_width=True):
        with st.spinner("Entrenando y comparando modelos con cross-validation..."):
            result = compare_models(dataset)

            from app.ml.risk_model import train_model_with_type_incremental

            best_model_type = MODEL_TYPE_MAPPING.get(result.best_model, "logistic")

            if st.session_state.data_source == "Base de Datos":
                train_model_with_type_incremental(dataset, best_model_type, use_saved=True)
            else:
                train_model_with_type_incremental(dataset, best_model_type, use_saved=False)

            st.session_state.result = result
            st.success("✅ Entrenamiento completado exitosamente!")
            st.rerun()

    if 'result' in st.session_state:
        st.success("✅ Modelo entrenado. Ve a la sección 'Resultados' para ver el análisis completo.")
        if st.button("Ver resultados →", type="secondary", use_container_width=True):
            go_to("results")


def page_results():
    st.markdown("<h1 class='section-header'>Resultados del entrenamiento</h1>", unsafe_allow_html=True)

    if 'result' not in st.session_state:
        st.warning("⚠️ Primero debes entrenar los modelos en la sección 'Entrenamiento'.")
        if st.button("Ir a entrenamiento", use_container_width=True):
            go_to("train")
        return

    result = st.session_state.result
    dataset_size = st.session_state.dataset_size
    data_source = st.session_state.data_source
    dataset = st.session_state.dataset

    status_label, status_kind = f1_status(result.best_f1)

    # Vista "hero": resumen autocontenido, visible sin scroll ni tabs.
    kpi1, kpi2, kpi3 = st.columns(3)
    with kpi1:
        metric_card("Modelo seleccionado", result.best_model)
    with kpi2:
        metric_card("F1-score", f"{result.best_f1:.3f}")
    with kpi3:
        st.markdown("<div class='metric-card'><div class='label'>Estado</div>", unsafe_allow_html=True)
        status_pill(status_label, status_kind)
        st.markdown("</div>", unsafe_allow_html=True)

    st.info(f"💡 {result.recommendation}")

    col_export, _ = st.columns([1, 2])
    with col_export:
        if REPORTLAB_AVAILABLE:
            pdf_buffer = generate_pdf_report(result, dataset_size, data_source)
            if pdf_buffer:
                st.download_button(
                    label="📄 Descargar reporte PDF",
                    data=pdf_buffer.getvalue(),
                    file_name=f"reporte_entrenamiento_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf",
                    mime="application/pdf",
                    type="primary",
                    use_container_width=True
                )
        else:
            st.warning("Para descargar PDF, instala reportlab: pip install reportlab")

    st.divider()

    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📊 Comparación", "📈 Curvas ROC", "🎯 Features y CV", "🔍 Detalle por modelo", "⚠️ Diagnóstico"
    ])

    with tab1:
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

        if result.statistical_tests:
            st.markdown("#### 🔬 Tests estadísticos (t-test pareado)")
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

    with tab2:
        col_roc, col_corr = st.columns(2)
        with col_roc:
            if result.roc_curves:
                st.markdown("#### Curvas ROC comparativas")
                fig = go.Figure()
                palette = ['#3b82f6', '#ef4444', '#10b981', '#f59e0b', '#8b5cf6']
                for i, (model_name, data) in enumerate(result.roc_curves.items()):
                    fig.add_trace(go.Scatter(
                        x=data['fpr'], y=data['tpr'], mode='lines',
                        name=f"{model_name} (AUC: {data['auc']:.3f})",
                        line=dict(color=palette[i % len(palette)], width=2)
                    ))
                fig.add_trace(go.Scatter(
                    x=[0, 1], y=[0, 1], mode='lines', name='Random',
                    line=dict(color='gray', width=1, dash='dash')
                ))
                fig.update_layout(
                    xaxis_title="False Positive Rate", yaxis_title="True Positive Rate",
                    legend=dict(x=0.55, y=0.08), height=380, margin=dict(t=10, b=10, l=10, r=10)
                )
                st.plotly_chart(fig, use_container_width=True, key="roc_curves")
        with col_corr:
            if result.correlation_matrix:
                st.markdown("#### Correlación entre features")
                corr_df = pd.DataFrame(result.correlation_matrix)
                fig = px.imshow(corr_df, text_auto=True, aspect="auto",
                               color_continuous_scale='RdBu_r', range_color=[-1, 1])
                fig.update_layout(height=380, margin=dict(t=10, b=10, l=10, r=10))
                st.plotly_chart(fig, use_container_width=True, key="correlation_heatmap")

    with tab3:
        col_fi, col_fold = st.columns(2)
        with col_fi:
            st.markdown("#### Feature importance por modelo")
            feature_importance_data = []
            for result_item in result.results:
                for feature, importance in result_item.feature_importance.items():
                    feature_importance_data.append({
                        "Feature": feature, "Modelo": result_item.model_name, "Importancia": importance
                    })
            fi_df = pd.DataFrame(feature_importance_data)
            fig = px.bar(fi_df, x="Importancia", y="Feature", color="Modelo", orientation="h", barmode="group")
            fig.update_layout(height=420, margin=dict(t=10, b=10, l=10, r=10))
            st.plotly_chart(fig, use_container_width=True, key="feature_importance_comparison")

        with col_fold:
            st.markdown("#### F1-score por fold")
            st.caption("Stratified K-Fold con n_splits ajustado dinámicamente según tamaño de dataset.")
            fold_data = []
            for result_item in result.results:
                for i, score in enumerate(result_item.f1_scores):
                    fold_data.append({"Modelo": result_item.model_name, "Fold": i + 1, "F1-Score": score})
            fold_df = pd.DataFrame(fold_data)
            fig = px.line(fold_df, x="Fold", y="F1-Score", color="Modelo", markers=True)
            fig.update_layout(height=420, margin=dict(t=10, b=10, l=10, r=10))
            st.plotly_chart(fig, use_container_width=True, key="fold_scores")

        st.markdown("#### Análisis de varianza entre folds")
        variance_data = []
        for result_item in result.results:
            variance_data.append({
                "Modelo": result_item.model_name,
                "Varianza F1": result_item.f1_std ** 2,
                "Estabilidad": "Alta" if result_item.f1_std < 0.05 else "Media" if result_item.f1_std < 0.1 else "Baja"
            })
        st.dataframe(pd.DataFrame(variance_data), use_container_width=True)

    with tab4:
        model_names = [r.model_name for r in result.results]
        selected_model = st.selectbox("Selecciona un modelo para ver el detalle", model_names)
        result_item = next(r for r in result.results if r.model_name == selected_model)

        col1, col2 = st.columns(2)
        with col1:
            st.markdown("#### Hiperparámetros")
            if result_item.hyperparameters:
                key_params = {
                    param: value for param, value in result_item.hyperparameters.items()
                    if param in ['n_estimators', 'max_depth', 'learning_rate', 'C', 'kernel',
                                 'hidden_layer_sizes', 'alpha']
                }
                st.json(key_params if key_params else result_item.hyperparameters)
            else:
                st.info("No hay hiperparámetros disponibles")

        with col2:
            st.markdown("#### Matriz de confusión")
            if result_item.confusion_matrix:
                cm = np.array(result_item.confusion_matrix)
                fig = px.imshow(cm, text_auto=True, aspect="auto", color_continuous_scale='Blues',
                               labels=dict(x="Predicho", y="Real", color="Count"))
                fig.update_layout(height=320, margin=dict(t=10, b=10, l=10, r=10))
                st.plotly_chart(fig, use_container_width=True,
                               key=f"confusion_matrix_{selected_model.replace(' ', '_')}")
            else:
                st.info("Matriz de confusión no disponible")

        st.markdown("#### Performance detallada")
        perf_data = {
            "Métrica": ["F1-Score", "Accuracy", "Precision", "Recall", "ROC-AUC", "Tiempo entrenamiento"],
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

    with tab5:
        from app.ml.risk_model import _build_pipeline
        X = np.array([features_to_vector(f) for f in dataset])
        y = np.array([f.label for f in dataset])

        best_model_type = MODEL_TYPE_MAPPING.get(result.best_model, "logistic")
        pipeline = _build_pipeline(best_model_type)
        pipeline.fit(X, y)
        y_pred = pipeline.predict(X)

        st.caption(
            "Nota: este ajuste se hace sobre todo el dataset para inspección; "
            "los errores mostrados son en muestra (in-sample) y pueden ser optimistas "
            "respecto al desempeño real fuera de muestra."
        )

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

        col_err, col_perf = st.columns([1.3, 1])
        with col_err:
            st.markdown("#### Casos mal clasificados")
            if misclassified:
                st.warning(f"⚠️ Se encontraron {len(misclassified)} casos mal clasificados")
                st.dataframe(pd.DataFrame(misclassified), use_container_width=True, height=260)
            else:
                st.success("✅ No hay casos mal clasificados en el dataset de entrenamiento")

        with col_perf:
            st.markdown("#### Resumen de performance")
            perf_summary = []
            for result_item in result.results:
                perf_summary.append({
                    "Modelo": result_item.model_name,
                    "Tiempo (s)": f"{result_item.training_time:.2f}",
                    "Estabilidad CV": "Alta" if result_item.f1_std < 0.05 else "Media" if result_item.f1_std < 0.1 else "Baja"
                })
            st.dataframe(pd.DataFrame(perf_summary), use_container_width=True, height=260)

        st.divider()

        if hasattr(pipeline.named_steps['classifier'], 'predict_proba'):
            col_dist, col_thresh = st.columns(2)
            y_proba = pipeline.predict_proba(X)[:, 1]

            with col_dist:
                st.markdown("#### Distribución de probabilidades")
                fig = px.histogram(x=y_proba, color=y, nbins=30,
                                 labels={"x": "Probabilidad", "color": "Clase Real"})
                fig.update_layout(barmode='overlay', height=340, margin=dict(t=10, b=10, l=10, r=10))
                st.plotly_chart(fig, use_container_width=True, key="probability_distribution")

            with col_thresh:
                st.markdown("#### Métricas vs threshold")
                thresholds = np.arange(0.1, 0.9, 0.1)
                threshold_results = []
                for threshold in thresholds:
                    y_pred_thresh = (y_proba >= threshold).astype(int)
                    threshold_results.append({
                        "Threshold": threshold,
                        "F1": f1_score(y, y_pred_thresh, zero_division=0),
                        "Precision": precision_score(y, y_pred_thresh, zero_division=0),
                        "Recall": recall_score(y, y_pred_thresh, zero_division=0)
                    })
                threshold_df = pd.DataFrame(threshold_results)
                fig = px.line(threshold_df, x="Threshold", y=["F1", "Precision", "Recall"], markers=True)
                fig.update_layout(height=340, margin=dict(t=10, b=10, l=10, r=10))
                st.plotly_chart(fig, use_container_width=True, key="threshold_analysis")
        else:
            st.info("El modelo seleccionado no soporta predict_proba")

    st.divider()
    if st.button("🔄 Reentrenar modelos", type="secondary", use_container_width=True):
        del st.session_state.result
        st.rerun()


def main():
    inject_css()
    page_key = render_sidebar()

    pages = {
        "home": page_home,
        "load": page_load,
        "analysis": page_analysis,
        "train": page_train,
        "results": page_results,
    }
    pages[page_key]()


if __name__ == "__main__":
    main()

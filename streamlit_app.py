import streamlit as st
import sys
import os
import joblib
import requests
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
from sqlalchemy import create_engine, text
try:
    from mistralai import Mistral
    MISTRAL_AVAILABLE = True
    MISTRAL_API_VERSION = "nueva"
except ImportError:
    try:
        from mistralai import MistralClient
        MISTRAL_AVAILABLE = True
        MISTRAL_API_VERSION = "antigua"
    except ImportError:
        try:
            from mistralai.client import MistralClient
            MISTRAL_AVAILABLE = True
            MISTRAL_API_VERSION = "legacy"
        except ImportError:
            MISTRAL_AVAILABLE = False
            MISTRAL_API_VERSION = "no instalada"
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
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image, PageBreak
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
        return engine
    except Exception as e:
        return None

# Backend API configuration
BACKEND_API_URL = os.getenv("BACKEND_API_URL", "http://localhost:8000")

def upload_model_to_backend(model_path):
    """Upload trained model to backend API"""
    try:
        # Load the model
        model = joblib.load(model_path)
        
        # Save to bytes buffer
        model_buffer = BytesIO()
        joblib.dump(model, model_buffer)
        model_buffer.seek(0)
        
        # Upload to backend
        files = {'file': ('risk_model.joblib', model_buffer, 'application/octet-stream')}
        response = requests.post(f"{BACKEND_API_URL}/api/risk/upload-model", files=files)
        
        if response.status_code == 200:
            return True, "Model uploaded successfully"
        else:
            return False, f"Upload failed: {response.text}"
    except Exception as e:
        return False, f"Upload error: {str(e)}"

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

def get_mistral_explanation_best_model(result):
    """Get AI explanation for the best model using Mistral"""
    if not MISTRAL_AVAILABLE:
        return "Mistral AI no está disponible. Instala mistralai: pip install mistralai"
    
    api_key = os.getenv("MISTRAL_API_KEY")
    if not api_key:
        return "API key de Mistral no configurada. Agrega MISTRAL_API_KEY al archivo .env"
    
    try:
        # Try new API (mistralai >= 1.0.0)
        try:
            from mistralai import Mistral
            client = Mistral(api_key=api_key)
            
            # Prepare prompt for best model explanation
            prompt = f"""
Analiza el rendimiento del mejor modelo de Machine Learning para predicción de riesgo de morosidad:

**Mejor Modelo:** {result.best_model}
**F1-Score:** {result.best_f1:.3f}
**Recomendación:** {result.recommendation}

Explica en lenguaje claro y conciso (máximo 3 párrafos):
1. ¿Qué significa el rendimiento del modelo en términos prácticos para el negocio?
2. ¿Cuáles son las fortalezas principales de este modelo?
3. ¿Qué riesgos o limitaciones se deben considerar al implementarlo?
"""
            
            response = client.chat.complete(
                model="mistral-small-latest",
                messages=[
                    {"role": "user", "content": prompt}
                ],
                max_tokens=400
            )
            
            return response.choices[0].message.content
            
        except ImportError:
            # Fallback to old API
            from mistralai.client import MistralClient
            client = MistralClient(api_key=api_key)
            
            prompt = f"""
Analiza el rendimiento del mejor modelo de Machine Learning para predicción de riesgo de morosidad:

**Mejor Modelo:** {result.best_model}
**F1-Score:** {result.best_f1:.3f}
**Recomendación:** {result.recommendation}

Explica en lenguaje claro y conciso (máximo 3 párrafos):
1. ¿Qué significa el rendimiento del modelo en términos prácticos para el negocio?
2. ¿Cuáles son las fortalezas principales de este modelo?
3. ¿Qué riesgos o limitaciones se deben considerar al implementarlo?
"""
            
            response = client.chat.complete(
                model="mistral-small-latest",
                messages=[
                    {"role": "user", "content": prompt}
                ],
                max_tokens=400
            )
            
            return response.choices[0].message.content
        
    except Exception as e:
        return f"Error al obtener explicación de Mistral: {str(e)}"


def get_mistral_explanation_comparison(result):
    """Get AI explanation for model comparison using Mistral"""
    if not MISTRAL_AVAILABLE:
        return "Mistral AI no está disponible. Instala mistralai: pip install mistralai"
    
    api_key = os.getenv("MISTRAL_API_KEY")
    if not api_key:
        return "API key de Mistral no configurada. Agrega MISTRAL_API_KEY al archivo .env"
    
    try:
        # Try new API (mistralai >= 1.0.0)
        try:
            from mistralai import Mistral
            client = Mistral(api_key=api_key)
            
            # Prepare prompt for comparison explanation
            prompt = f"""
Analiza la comparación de modelos de Machine Learning para predicción de riesgo de morosidad:

**Mejor Modelo:** {result.best_model} (F1={result.best_f1:.3f})

**Comparación de Modelos:**
"""
            for r in result.results:
                prompt += f"- {r.model_name}: F1={r.f1_mean:.3f}±{r.f1_std:.3f}, Accuracy={r.accuracy_mean:.3f}±{r.accuracy_std:.3f}, Tiempo={r.training_time:.2f}s\n"
            
            prompt += """
Explica en lenguaje claro y conciso (máximo 3 párrafos):
1. ¿Cuál es la diferencia principal entre los modelos en términos de rendimiento?
2. ¿Qué modelo ofrece el mejor balance entre rendimiento y eficiencia?
3. ¿Qué factores deberían considerarse al elegir entre los modelos principales?
"""
            
            response = client.chat.complete(
                model="mistral-small-latest",
                messages=[
                    {"role": "user", "content": prompt}
                ],
                max_tokens=400
            )
            
            return response.choices[0].message.content
            
        except ImportError:
            # Fallback to old API
            from mistralai.client import MistralClient
            client = MistralClient(api_key=api_key)
            
            prompt = f"""
Analiza la comparación de modelos de Machine Learning para predicción de riesgo de morosidad:

**Mejor Modelo:** {result.best_model} (F1={result.best_f1:.3f})

**Comparación de Modelos:**
"""
            for r in result.results:
                prompt += f"- {r.model_name}: F1={r.f1_mean:.3f}±{r.f1_std:.3f}, Accuracy={r.accuracy_mean:.3f}±{r.accuracy_std:.3f}, Tiempo={r.training_time:.2f}s\n"
            
            prompt += """
Explica en lenguaje claro y conciso (máximo 3 párrafos):
1. ¿Cuál es la diferencia principal entre los modelos en términos de rendimiento?
2. ¿Qué modelo ofrece el mejor balance entre rendimiento y eficiencia?
3. ¿Qué factores deberían considerarse al elegir entre los modelos principales?
"""
            
            response = client.chat.complete(
                model="mistral-small-latest",
                messages=[
                    {"role": "user", "content": prompt}
                ],
                max_tokens=400
            )
            
            return response.choices[0].message.content
        
    except Exception as e:
        return f"Error al obtener explicación de Mistral: {str(e)}"


def get_mistral_explanation_statistical(result):
    """Get AI explanation for statistical tests using Mistral"""
    if not MISTRAL_AVAILABLE:
        return "Mistral AI no está disponible. Instala mistralai: pip install mistralai"
    
    api_key = os.getenv("MISTRAL_API_KEY")
    if not api_key:
        return "API key de Mistral no configurada. Agrega MISTRAL_API_KEY al archivo .env"
    
    try:
        # Try new API (mistralai >= 1.0.0)
        try:
            from mistralai import Mistral
            client = Mistral(api_key=api_key)
            
            # Prepare prompt for statistical tests explanation
            prompt = f"""
Analiza los resultados de tests estadísticos para modelos de Machine Learning:

**Mejor Modelo:** {result.best_model}

**Tests Estadísticos (t-test):**
"""
            if result.statistical_tests:
                for test_name, test_data in result.statistical_tests.items():
                    significance = "Sí" if test_data.get('significant', False) else "No"
                    prompt += f"- {test_name}: p-value={test_data.get('p_value', 0):.4f}, significativo={significance}\n"
            
            prompt += """
Explica en lenguaje claro y conciso (máximo 2 párrafos):
1. ¿Qué indican los tests estadísticos sobre las diferencias entre modelos?
2. ¿Qué conclusión práctica se puede extraer de estos resultados?
"""
            
            response = client.chat.complete(
                model="mistral-small-latest",
                messages=[
                    {"role": "user", "content": prompt}
                ],
                max_tokens=300
            )
            
            return response.choices[0].message.content
            
        except ImportError:
            # Fallback to old API
            from mistralai.client import MistralClient
            client = MistralClient(api_key=api_key)
            
            prompt = f"""
Analiza los resultados de tests estadísticos para modelos de Machine Learning:

**Mejor Modelo:** {result.best_model}

**Tests Estadísticos (t-test):**
"""
            if result.statistical_tests:
                for test_name, test_data in result.statistical_tests.items():
                    significance = "Sí" if test_data.get('significant', False) else "No"
                    prompt += f"- {test_name}: p-value={test_data.get('p_value', 0):.4f}, significativo={significance}\n"
            
            prompt += """
Explica en lenguaje claro y conciso (máximo 2 párrafos):
1. ¿Qué indican los tests estadísticos sobre las diferencias entre modelos?
2. ¿Qué conclusión práctica se puede extraer de estos resultados?
"""
            
            response = client.chat.complete(
                model="mistral-small-latest",
                messages=[
                    {"role": "user", "content": prompt}
                ],
                max_tokens=300
            )
            
            return response.choices[0].message.content
        
    except Exception as e:
        return f"Error al obtener explicación de Mistral: {str(e)}"


def get_mistral_explanation(result):
    """Get AI explanation of results using Mistral (legacy function for compatibility)"""
    return get_mistral_explanation_best_model(result)


def generate_pdf_report(result, dataset_size, data_source, mistral_best_model=None, mistral_comparison=None, mistral_statistical=None):
    """Generate PDF report with training results"""
    if not REPORTLAB_AVAILABLE:
        return None

    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer, 
        pagesize=letter, 
        leftMargin=72, 
        rightMargin=72, 
        topMargin=72, 
        bottomMargin=72
    )
    styles = getSampleStyleSheet()

    # Custom styles - University/Professional design
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=16,
        textColor=colors.HexColor('#1a237e'),  # Dark blue
        alignment=TA_CENTER,
        spaceAfter=30,
        fontName='Helvetica-Bold',
        leading=20
    )

    subtitle_style = ParagraphStyle(
        'CustomSubtitle',
        parent=styles['Heading2'],
        fontSize=12,
        textColor=colors.HexColor('#424242'),  # Dark gray
        alignment=TA_CENTER,
        spaceAfter=25,
        fontName='Helvetica',
        leading=16
    )

    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontSize=12,
        textColor=colors.HexColor('#1565c0'),  # Medium blue
        spaceAfter=12,
        spaceBefore=20,
        fontName='Helvetica-Bold',
        leading=16,
        borderPadding=5,
        borderWidth=1,
        borderColor=colors.HexColor('#e0e0e0')
    )

    subheading_style = ParagraphStyle(
        'CustomSubheading',
        parent=styles['Heading3'],
        fontSize=11,
        textColor=colors.HexColor('#424242'),
        spaceAfter=10,
        spaceBefore=15,
        fontName='Helvetica-Bold',
        leading=14
    )

    normal_style = ParagraphStyle(
        'CustomNormal',
        parent=styles['Normal'],
        fontSize=10,
        textColor=colors.HexColor('#616161'),
        spaceAfter=10,
        leading=14,
        fontName='Helvetica'
    )

    table_header_style = ParagraphStyle(
        'TableHeader',
        parent=styles['Normal'],
        fontSize=9,
        textColor=colors.white,
        fontName='Helvetica-Bold',
        leading=12
    )

    table_cell_style = ParagraphStyle(
        'TableCell',
        parent=styles['Normal'],
        fontSize=9,
        textColor=colors.HexColor('#424242'),
        leading=12,
        fontName='Helvetica'
    )

    content = []

    # University header
    header_data = [
        [Paragraph("<b>UNIVERSIDAD</b>", ParagraphStyle('Header', fontSize=14, textColor=colors.HexColor('#1a237e'), fontName='Helvetica-Bold'))],
        [Paragraph("Laboratorio de Machine Learning", ParagraphStyle('Header', fontSize=10, textColor=colors.HexColor('#757575'), fontName='Helvetica'))],
        [Paragraph("Sistema de Predicción de Riesgo de Morosidad", ParagraphStyle('Header', fontSize=9, textColor=colors.HexColor('#9e9e9e'), fontName='Helvetica'))]
    ]
    header_table = Table(header_data, colWidths=[400])
    header_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    content.append(header_table)
    content.append(Spacer(1, 20))

    # Decorative line
    content.append(Paragraph("<hr/>", ParagraphStyle('Line', fontSize=6, textColor=colors.HexColor('#e0e0e0'))))
    content.append(Spacer(1, 15))

    # Title
    content.append(Paragraph("REPORTE DE ENTRENAMIENTO DE MODELOS", title_style))
    content.append(Paragraph("Análisis Comparativo de Algoritmos de Machine Learning", subtitle_style))
    content.append(Spacer(1, 20))

    # Metadata box
    metadata_data = [
        ["Fecha de Generación", datetime.now().strftime('%Y-%m-%d %H:%M:%S')],
        ["Fuente de Datos", data_source],
        ["Tamaño del Dataset", f"{dataset_size} muestras"],
        ["Número de Modelos Evaluados", str(len(result.results))]
    ]
    metadata_table = Table(metadata_data, colWidths=[2.5, 3])
    metadata_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f5f5f5')),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.HexColor('#424242')),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e0e0e0')),
        ('ROWBACKGROUNDS', (0, 0), (-1, -1), [colors.white, colors.HexColor('#fafafa')]),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    content.append(metadata_table)
    content.append(Spacer(1, 25))

    # Best Model
    content.append(Paragraph("Mejor Modelo", heading_style))
    best_model_data = [
        ["Modelo", result.best_model],
        ["F1-Score", f"{result.best_f1:.3f}"],
        ["Estado", "Excelente" if result.best_f1 > 0.8 else "Bueno" if result.best_f1 > 0.7 else "Moderado"]
    ]
    best_model_table = Table(best_model_data, colWidths=[3, 2])
    best_model_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#e8eaf6')),
        ('TEXTCOLOR', (0, 0), (0, -1), colors.HexColor('#1a237e')),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (0, -1), 10),
        ('BACKGROUND', (1, 0), (1, -1), colors.HexColor('#fafafa')),
        ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
        ('FONTSIZE', (1, 0), (1, -1), 10),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e0e0e0')),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    content.append(best_model_table)
    content.append(Spacer(1, 20))

    # Recommendation
    content.append(Paragraph("Recomendación", subheading_style))
    content.append(Paragraph(result.recommendation, normal_style))
    content.append(Spacer(1, 20))

    # AI Explanation - Best Model
    if mistral_best_model:
        content.append(Paragraph("Análisis con Inteligencia Artificial - Mejor Modelo", subheading_style))
        content.append(Paragraph(mistral_best_model, normal_style))
        content.append(Spacer(1, 20))

    content.append(PageBreak())

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

    comparison_table = Table(comparison_data, colWidths=[3.0, 1.2, 1.2, 1.2, 1.2, 1.2, 0.8])
    comparison_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1565c0')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 9),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
        ('TOPPADDING', (0, 0), (-1, 0), 8),
        ('BACKGROUND', (0, 1), (-1, -1), colors.white),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 9),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e0e0e0')),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#fafafa')]),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 1), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 4),
    ]))
    content.append(comparison_table)
    content.append(Spacer(1, 20))

    # AI Explanation - Comparison
    if mistral_comparison:
        content.append(Paragraph("Análisis con Inteligencia Artificial - Comparación de Modelos", subheading_style))
        content.append(Paragraph(mistral_comparison, normal_style))
        content.append(Spacer(1, 20))

    # Statistical Tests (t-test)
    if result.statistical_tests:
        content.append(Paragraph("Tests Estadísticos (t-test pareado)", subheading_style))
        tests_data = [["Comparación", "t-statistic", "p-value", "Significativo"]]
        for test_name, test_data in result.statistical_tests.items():
            t_stat = test_data.get('t_statistic', 0.0)
            p_val = test_data.get('p_value', 1.0)
            tests_data.append([
                test_name,
                f"{t_stat:.3f}" if not np.isnan(t_stat) else "N/A",
                f"{p_val:.4f}" if not np.isnan(p_val) else "N/A",
                "Sí" if test_data.get('significant', False) else "No"
            ])

        tests_table = Table(tests_data, colWidths=[3, 1.5, 1.5, 1.5])
        tests_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1565c0')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
            ('TOPPADDING', (0, 0), (-1, 0), 8),
            ('BACKGROUND', (0, 1), (-1, -1), colors.white),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e0e0e0')),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#fafafa')]),
            ('LEFTPADDING', (0, 0), (-1, -1), 6),
            ('RIGHTPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 1), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 1), (-1, -1), 4),
        ]))
        content.append(tests_table)
        content.append(Spacer(1, 20))

    # Wilcoxon Tests
    if result.wilcoxon_tests:
        content.append(Paragraph("Wilcoxon Signed-Rank Test (no paramétrico)", subheading_style))
        wilcoxon_data = [["Comparación", "statistic", "p-value", "Significativo"]]
        for test_name, test_data in result.wilcoxon_tests.items():
            if isinstance(test_data, dict) and 'statistic' in test_data:
                stat = test_data.get('statistic', 0.0)
                p_val = test_data.get('p_value', 1.0)
                wilcoxon_data.append([
                    test_name,
                    f"{stat:.3f}" if not np.isnan(stat) else "N/A",
                    f"{p_val:.4f}" if not np.isnan(p_val) else "N/A",
                    "Sí" if test_data.get('significant', False) else "No"
                ])

        if len(wilcoxon_data) > 1:
            wilcoxon_table = Table(wilcoxon_data, colWidths=[3, 1.5, 1.5, 1.5])
            wilcoxon_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1565c0')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 9),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
                ('TOPPADDING', (0, 0), (-1, 0), 8),
                ('BACKGROUND', (0, 1), (-1, -1), colors.white),
                ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 1), (-1, -1), 9),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e0e0e0')),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#fafafa')]),
                ('LEFTPADDING', (0, 0), (-1, -1), 6),
                ('RIGHTPADDING', (0, 0), (-1, -1), 6),
                ('TOPPADDING', (0, 1), (-1, -1), 4),
                ('BOTTOMPADDING', (0, 1), (-1, -1), 4),
            ]))
            content.append(wilcoxon_table)
            content.append(Spacer(1, 20))

    # AI Explanation - Statistical Tests
    if mistral_statistical:
        content.append(Paragraph("Análisis con Inteligencia Artificial - Tests Estadísticos", subheading_style))
        content.append(Paragraph(mistral_statistical, normal_style))
        content.append(Spacer(1, 20))

    # McNemar Tests
    if result.mcnemar_tests and not ("error" in result.mcnemar_tests and isinstance(result.mcnemar_tests["error"], str)):
        content.append(Paragraph("McNemar's Test (clasificadores binarios)", heading_style))
        mcnemar_data = [["Comparación", "statistic", "p-value", "Significativo"]]
        for test_name, test_data in result.mcnemar_tests.items():
            if isinstance(test_data, dict) and 'statistic' in test_data:
                stat = test_data.get('statistic', 0.0)
                p_val = test_data.get('p_value', 1.0)
                mcnemar_data.append([
                    test_name,
                    f"{stat:.3f}" if not np.isnan(stat) else "N/A",
                    f"{p_val:.4f}" if not np.isnan(p_val) else "N/A",
                    "Sí" if test_data.get('significant', False) else "No"
                ])

        if len(mcnemar_data) > 1:
            mcnemar_table = Table(mcnemar_data, colWidths=[3, 1.5, 1.5, 1.5])
            mcnemar_table.setStyle(TableStyle([
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
            content.append(mcnemar_table)
            content.append(Spacer(1, 20))

    # Bootstrap Confidence Intervals
    if result.bootstrap_intervals:
        content.append(Paragraph("Bootstrap Confidence Intervals (95%)", subheading_style))
        bootstrap_data = [["Modelo", "F1 Lower", "F1 Upper", "Intervalo"]]
        for model_name, interval_data in result.bootstrap_intervals.items():
            bootstrap_data.append([
                model_name,
                f"{interval_data['f1_lower']:.3f}",
                f"{interval_data['f1_upper']:.3f}",
                f"[{interval_data['f1_lower']:.3f}, {interval_data['f1_upper']:.3f}]"
            ])

        bootstrap_table = Table(bootstrap_data, colWidths=[2.5, 1.5, 1.5, 2])
        bootstrap_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1565c0')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
            ('TOPPADDING', (0, 0), (-1, 0), 8),
            ('BACKGROUND', (0, 1), (-1, -1), colors.white),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e0e0e0')),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#fafafa')]),
            ('LEFTPADDING', (0, 0), (-1, -1), 6),
            ('RIGHTPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 1), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 1), (-1, -1), 4),
        ]))
        content.append(bootstrap_table)
        content.append(Spacer(1, 20))

    # Variance Analysis
    if result.variance_analysis:
        content.append(Paragraph("Análisis de Varianza (Estabilidad)", heading_style))
        variance_data = [["Modelo", "Varianza F1", "Std F1", "CV", "Estabilidad"]]
        for model_name, variance_data_item in result.variance_analysis.items():
            variance_data.append([
                model_name,
                f"{variance_data_item['f1_variance']:.4f}",
                f"{variance_data_item['f1_std']:.4f}",
                f"{variance_data_item['f1_cv']:.3f}",
                variance_data_item['stability']
            ])

        variance_table = Table(variance_data, colWidths=[2.5, 1.5, 1.5, 1, 1.5])
        variance_table.setStyle(TableStyle([
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
        content.append(variance_table)
        content.append(Spacer(1, 20))

    # Feature Importance Stability
    if result.feature_importance_stability:
        content.append(Paragraph("Estabilidad de Feature Importance", heading_style))
        stability_data = [["Feature", "Media", "Std", "CV", "Estabilidad"]]
        for feature, stability_data_item in result.feature_importance_stability.items():
            # Ensure all values are present and valid
            mean_val = stability_data_item.get('mean', 0.0)
            std_val = stability_data_item.get('std', 0.0)
            cv_val = stability_data_item.get('cv', 0.0)
            stability_val = stability_data_item.get('stability', 'Desconocida')
            
            # Only add if we have valid data
            if not (np.isnan(mean_val) or np.isnan(std_val) or np.isnan(cv_val)):
                stability_data.append([
                    feature,
                    f"{mean_val:.3f}" if not np.isnan(mean_val) else "N/A",
                    f"{std_val:.3f}" if not np.isnan(std_val) else "N/A",
                    f"{cv_val:.3f}" if not np.isnan(cv_val) else "N/A",
                    stability_val
                ])

        if len(stability_data) > 1:
            stability_table = Table(stability_data, colWidths=[2.5, 1, 1, 1, 1.5])
        stability_table.setStyle(TableStyle([
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
        content.append(stability_table)
        content.append(Spacer(1, 20))

    content.append(PageBreak())

    # Methodology Section
    content.append(Paragraph("Metodología", heading_style))
    methodology_text = """
    <b>Validación Cruzada:</b> Stratified K-Fold con n_splits ajustado dinámicamente según tamaño del dataset.
    <b>Métricas:</b> F1-score, accuracy, precision, recall y ROC-AUC.
    <b>Tests Estadísticos:</b> t-test pareado, Wilcoxon signed-rank test, Bootstrap confidence intervals.
    <b>Análisis de Estabilidad:</b> Varianza entre folds, coeficiente de variación.
    <b>Curvas de Aprendizaje:</b> Rendimiento vs tamaño del dataset.
    <b>Calibración:</b> Curvas de calibración de probabilidades predichas.
    """
    content.append(Paragraph(methodology_text, normal_style))
    content.append(Spacer(1, 20))

    # Footer
    content.append(Paragraph(f"Generado por ML Risk Scoring - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", 
                            ParagraphStyle('Footer', parent=styles['Normal'], fontSize=8, textColor=colors.gray, alignment=TA_CENTER)))

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

    # Custom CSS for professional styling with dark mode support
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

    # Helper functions for UI components
    def metric_card(label, value, hint=None):
        if hint:
            st.markdown(
                f"""<div class="metric-card">
                        <div class="label">{label}</div>
                        <div class="value">{value}</div>
                        <div class="hint">{hint}</div>
                    </div>""",
                unsafe_allow_html=True
            )
        else:
            st.markdown(
                f"""<div class="metric-card">
                        <div class="label">{label}</div>
                        <div class="value">{value}</div>
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

        # Mistral AI status
        if MISTRAL_AVAILABLE:
            st.success(f"✅ Mistral AI disponible (API: {MISTRAL_API_VERSION})")
        else:
            st.warning(f"⚠️ Mistral AI no disponible (API: {MISTRAL_API_VERSION})")

        st.divider()

        # KPIs in grid layout using metric_card
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

        # Info cards with app.py design
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
        if st.button("Comenzar →", type="primary", width='stretch'):
            st.session_state.page = "📁 Cargar Datos"
            st.rerun()

    elif page == "📁 Cargar Datos":
        st.markdown("<h1 class='section-header'>Carga de Datos</h1>", unsafe_allow_html=True)

        data_source = st.radio(
            "Selecciona la fuente de datos para el entrenamiento:",
            ["📄 Archivo CSV (Primer entrenamiento)", "📊 Base de Datos (Incremental)"],
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
            if st.button("Ir a Análisis de Dataset →", type="primary", width='stretch'):
                st.session_state.page = "📈 Análisis Dataset"
                st.rerun()

    elif page == "📈 Análisis Dataset":
        st.markdown("<h1 class='section-header'>Análisis del Dataset</h1>", unsafe_allow_html=True)

        if 'dataset' not in st.session_state or st.session_state.dataset is None:
            st.warning("⚠️ Primero debes cargar los datos en la sección 'Cargar Datos'.")
            if st.button("Ir a Cargar Datos", width='stretch'):
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

        # Summary KPIs in grid using metric_card
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
            balance_label = "Balanceado" if 15 <= balance <= 85 else "Desbalanceado"
            balance_kind = "good" if 15 <= balance <= 85 else "warn"
            metric_card("Balance de clases", f"{balance:.1f}%")
            status_pill(balance_label, balance_kind)

        st.divider()

        # Distribution and Statistics in grid
        col1, col2 = st.columns(2)
        
        with col1:
            st.container(border=True).markdown("### 📈 Distribución de Clases")
            class_counts = dataset_df['label'].value_counts()
            fig = px.pie(values=class_counts.values, names=['Bajo Riesgo', 'Alto Riesgo'] if 0 in class_counts.index else ['Alto Riesgo'], hole=0.3)
            fig.update_layout(title="Balance de Clases", showlegend=True)
            st.plotly_chart(fig, width='stretch', key="class_distribution")
            
        with col2:
            st.container(border=True).markdown("### 📊 Estadísticas Descriptivas")
            st.dataframe(dataset_df.describe(), width='stretch')

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
            st.plotly_chart(fig, width='stretch', key=f"feature_dist_{selected_feature}")
        
        with col2:
            st.container(border=True).markdown("### 📈 Estadísticas por Clase")
            stats_by_class = dataset_df.groupby('label')[selected_feature].describe()
            st.dataframe(stats_by_class, width='stretch')
            
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
        st.plotly_chart(fig_melt, width='stretch', key="boxplot_comparison")

        st.divider()
        if st.button("Ir a Entrenamiento de Modelos →", type="primary", width='stretch'):
            st.session_state.page = "🤖 Entrenamiento"
            st.rerun()

    elif page == "🤖 Entrenamiento":
        st.markdown("<h1 class='section-header'>Entrenamiento de Modelos</h1>", unsafe_allow_html=True)

        if 'dataset' not in st.session_state or st.session_state.dataset is None:
            st.warning("⚠️ Primero debes cargar los datos en la sección 'Cargar Datos'.")
            if st.button("Ir a Cargar Datos", width='stretch'):
                st.session_state.page = "📁 Cargar Datos"
                st.rerun()
            return

        dataset = st.session_state.dataset

        # Dataset info in grid using metric_card
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

        # Training action
        if st.button("🚀 Entrenar y Comparar 5 Modelos", type="primary", width='stretch'):
            progress_bar = st.progress(0, text="Iniciando entrenamiento...")
            status_text = st.empty()
            
            try:
                status_text.text("🔄 Preparando dataset...")
                progress_bar.progress(10, text="Preparando dataset...")
                
                # Validate dataset has at least 2 classes
                labels = [f.label for f in dataset]
                unique_labels = set(labels)
                if len(unique_labels) < 2:
                    progress_bar.empty()
                    status_text.empty()
                    st.error(f"❌ El dataset debe contener al menos 2 clases para el entrenamiento. Clases encontradas: {unique_labels}")
                    st.warning("⚠️ Por favor carga un dataset con clientes de alto riesgo (label=1) y bajo riesgo (label=0).")
                    return
                
                status_text.text("🤖 Entrenando Logistic Regression...")
                progress_bar.progress(20, text="Entrenando Logistic Regression...")
                
                status_text.text("🤖 Entrenando Random Forest...")
                progress_bar.progress(35, text="Entrenando Random Forest...")
                
                status_text.text("🤖 Entrenando Support Vector Machine...")
                progress_bar.progress(50, text="Entrenando Support Vector Machine...")
                
                status_text.text("🤖 Entrenando Gradient Boosting...")
                progress_bar.progress(65, text="Entrenando Gradient Boosting...")
                
                status_text.text("🤖 Entrenando Neural Network (MLP)...")
                progress_bar.progress(80, text="Entrenando Neural Network (MLP)...")
                
                status_text.text("📊 Realizando tests estadísticos...")
                progress_bar.progress(90, text="Realizando tests estadísticos...")
                
                result = compare_models(dataset)
                
                status_text.text("💾 Guardando mejor modelo...")
                progress_bar.progress(95, text="Guardando mejor modelo...")
                
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

                # Upload model to backend for production use
                status_text.text("📤 Subiendo modelo al backend...")
                progress_bar.progress(98, text="Subiendo modelo al backend...")
                
                from app.ml.risk_model import MODEL_PATH
                upload_success, upload_message = upload_model_to_backend(MODEL_PATH)
                
                if upload_success:
                    st.info(f"✅ {upload_message}")
                    st.session_state.upload_status = "success"
                else:
                    st.warning(f"⚠️ {upload_message}")
                    st.session_state.upload_status = "failed"

                progress_bar.progress(100, text="✅ Entrenamiento completado!")
                status_text.text("✅ Entrenamiento completado exitosamente!")
                
                st.session_state.result = result
                st.success("✅ Entrenamiento completado exitosamente!")
                st.rerun()
                
            except Exception as e:
                progress_bar.empty()
                status_text.empty()
                st.error(f"❌ Error durante el entrenamiento: {str(e)}")

        if 'result' in st.session_state:
            upload_status = st.session_state.get('upload_status', 'unknown')
            if upload_status == 'success':
                st.success("✅ Modelo entrenado y subido al backend exitosamente.")
            elif upload_status == 'failed':
                st.warning("⚠️ Modelo entrenado pero no se pudo subir al backend.")
            else:
                st.success("✅ Modelo entrenado.")
            
            if st.button("Ver Resultados →", type="secondary", width='stretch'):
                st.session_state.page = "📋 Resultados"
                st.rerun()

    elif page == "📋 Resultados":
        st.markdown("<h1 class='section-header'>Resultados del Entrenamiento</h1>", unsafe_allow_html=True)

        if 'result' not in st.session_state:
            st.warning("⚠️ Primero debes entrenar los modelos en la sección 'Entrenamiento'.")
            if st.button("Ir a Entrenamiento", width='stretch'):
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
            # Hero view with metric_card and status_pill
            status_label, status_kind = f1_status(result.best_f1)

            kpi1, kpi2, kpi3 = st.columns(3)
            with kpi1:
                metric_card("Modelo seleccionado", result.best_model)
            with kpi2:
                metric_card("F1-score", f"{result.best_f1:.3f}")
            with kpi3:
                st.markdown(
                    f"""<div class="metric-card">
                        <div class="label">Estado</div>
                        <div class="value"></div>
                    </div>""",
                    unsafe_allow_html=True
                )
                status_pill(status_label, status_kind)

            st.info(f"💡 {result.recommendation}")

            st.divider()

            # AI Explanation with Mistral
            st.container(border=True).markdown("### 🤖 Explicación con IA (Mistral)")
            
            if not MISTRAL_AVAILABLE:
                st.warning("⚠️ Mistral AI no está disponible. Instala mistralai: pip install mistralai")
            elif not os.getenv("MISTRAL_API_KEY"):
                st.warning("⚠️ API key de Mistral no configurada. Agrega MISTRAL_API_KEY al archivo .env")
            else:
                if st.button("🧠 Generar explicación con IA", type="secondary", width='stretch'):
                    with st.spinner("Generando explicación con Mistral AI..."):
                        explanation_best = get_mistral_explanation_best_model(result)
                        explanation_comparison = get_mistral_explanation_comparison(result)
                        explanation_statistical = get_mistral_explanation_statistical(result)
                        st.session_state.mistral_best_model = explanation_best
                        st.session_state.mistral_comparison = explanation_comparison
                        st.session_state.mistral_statistical = explanation_statistical
                
                if 'mistral_best_model' in st.session_state:
                    st.markdown("#### 🎯 Mejor Modelo")
                    st.markdown(st.session_state.mistral_best_model)
                    st.markdown("#### 📊 Comparación de Modelos")
                    st.markdown(st.session_state.mistral_comparison)
                    st.markdown("#### 📈 Tests Estadísticos")
                    st.markdown(st.session_state.mistral_statistical)
                    st.caption("Explicación generada por Mistral AI")

            st.divider()

            col_export, _ = st.columns([1, 2])
            with col_export:
                if REPORTLAB_AVAILABLE:
                    mistral_best = st.session_state.get('mistral_best_model', None)
                    mistral_comp = st.session_state.get('mistral_comparison', None)
                    mistral_stat = st.session_state.get('mistral_statistical', None)
                    pdf_buffer = generate_pdf_report(result, dataset_size, data_source, mistral_best, mistral_comp, mistral_stat)
                    if pdf_buffer:
                        st.download_button(
                            label="📄 Descargar reporte PDF",
                            data=pdf_buffer.getvalue(),
                            file_name=f"reporte_entrenamiento_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf",
                            mime="application/pdf",
                            type="primary",
                            width='stretch'
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
            st.dataframe(results_df, width='stretch')

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
                st.dataframe(tests_df, width='stretch')

            # Wilcoxon tests
            if result.wilcoxon_tests:
                st.container(border=True).markdown("### 🔬 Wilcoxon Signed-Rank Test (no paramétrico)")
                wilcoxon_df = pd.DataFrame([
                    {
                        "Comparación": test,
                        "statistic": f"{data['statistic']:.3f}" if 'statistic' in data else "N/A",
                        "p-value": f"{data['p_value']:.4f}" if 'p_value' in data else "N/A",
                        "Significativo": "✅ Sí" if data.get('significant', False) else "❌ No"
                    }
                    for test, data in result.wilcoxon_tests.items()
                ])
                st.dataframe(wilcoxon_df, width='stretch')

            # McNemar tests
            if result.mcnemar_tests:
                # Check if there's an error message (statsmodels not installed)
                if "error" in result.mcnemar_tests and isinstance(result.mcnemar_tests["error"], str):
                    # Don't show the section if statsmodels is not installed
                    pass
                else:
                    st.container(border=True).markdown("### 🔬 McNemar's Test (clasificadores binarios)")
                    mcnemar_data = []
                    for test, data in result.mcnemar_tests.items():
                        if isinstance(data, dict):
                            mcnemar_data.append({
                                "Comparación": test,
                                "statistic": f"{data['statistic']:.3f}" if 'statistic' in data else "N/A",
                                "p-value": f"{data['p_value']:.4f}" if 'p_value' in data else "N/A",
                                "Significativo": "✅ Sí" if data.get('significant', False) else "❌ No"
                            })
                        else:
                            mcnemar_data.append({
                                "Comparación": test,
                                "statistic": "N/A",
                                "p-value": "N/A",
                                "Significativo": "N/A"
                            })
                    mcnemar_df = pd.DataFrame(mcnemar_data)
                    st.dataframe(mcnemar_df, width='stretch')

            # Bootstrap intervals
            if result.bootstrap_intervals:
                st.container(border=True).markdown("### 📊 Bootstrap Confidence Intervals (95%)")
                bootstrap_df = pd.DataFrame([
                    {
                        "Modelo": model,
                        "F1 Lower": f"{data['f1_lower']:.3f}",
                        "F1 Upper": f"{data['f1_upper']:.3f}",
                        "Intervalo": f"[{data['f1_lower']:.3f}, {data['f1_upper']:.3f}]"
                    }
                    for model, data in result.bootstrap_intervals.items()
                ])
                st.dataframe(bootstrap_df, width='stretch')

            # Variance analysis
            if result.variance_analysis:
                st.container(border=True).markdown("### 📈 Análisis de Varianza (Estabilidad)")
                variance_df = pd.DataFrame([
                    {
                        "Modelo": model,
                        "Varianza F1": f"{data['f1_variance']:.4f}",
                        "Std F1": f"{data['f1_std']:.4f}",
                        "CV": f"{data['f1_cv']:.3f}",
                        "Estabilidad": data['stability']
                    }
                    for model, data in result.variance_analysis.items()
                ])
                st.dataframe(variance_df, width='stretch')

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
                    st.plotly_chart(fig, width='stretch', key="roc_curves")
            
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
                    st.plotly_chart(fig, width='stretch', key="correlation_heatmap")

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
            st.plotly_chart(fig, width='stretch', key="feature_importance_comparison")

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
                st.plotly_chart(fig, width='stretch', key="fold_scores")
            
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
                st.dataframe(variance_df, width='stretch')

            st.divider()

            # Learning curves
            if result.learning_curves:
                st.container(border=True).markdown("### 📈 Learning Curves")
                st.info("Curvas de aprendizaje: rendimiento vs tamaño del dataset")
                
                for model_name, data in result.learning_curves.items():
                    if "error" not in data:
                        fig = go.Figure()
                        fig.add_trace(go.Scatter(
                            x=data['train_sizes'],
                            y=data['train_scores_mean'],
                            mode='lines+markers',
                            name='Train',
                            line=dict(color='blue')
                        ))
                        fig.add_trace(go.Scatter(
                            x=data['train_sizes'],
                            y=data['val_scores_mean'],
                            mode='lines+markers',
                            name='Validation',
                            line=dict(color='red')
                        ))
                        fig.update_layout(
                            title=f"Learning Curve - {model_name}",
                            xaxis_title="Tamaño del dataset",
                            yaxis_title="F1-Score",
                            height=400
                        )
                        st.plotly_chart(fig, width='stretch', key=f"learning_curve_{model_name.replace(' ', '_')}")

            st.divider()

            # Calibration curves
            if result.calibration_curves:
                st.container(border=True).markdown("### 📊 Calibration Curves")
                st.info("Curvas de calibración: verifican si las probabilidades están bien calibradas")
                
                for model_name, data in result.calibration_curves.items():
                    if "error" not in data:
                        fig = go.Figure()
                        fig.add_trace(go.Scatter(
                            x=data['mean_predicted_value'],
                            y=data['fraction_of_positives'],
                            mode='lines+markers',
                            name=model_name,
                            line=dict(width=2)
                        ))
                        fig.add_trace(go.Scatter(
                            x=[0, 1],
                            y=[0, 1],
                            mode='lines',
                            name='Perfect Calibration',
                            line=dict(color='gray', dash='dash')
                        ))
                        fig.update_layout(
                            title=f"Calibration Curve - {model_name}",
                            xaxis_title="Probabilidad predicha media",
                            yaxis_title="Fracción de positivos",
                            height=400
                        )
                        st.plotly_chart(fig, width='stretch', key=f"calibration_curve_{model_name.replace(' ', '_')}")

            st.divider()

            # Feature importance stability
            if result.feature_importance_stability:
                st.container(border=True).markdown("### 🎯 Estabilidad de Feature Importance")
                st.info("Análisis de estabilidad de la importancia de features entre modelos")
                
                stability_data = []
                for feature, data in result.feature_importance_stability.items():
                    stability_data.append({
                        "Feature": feature,
                        "Media": f"{data['mean']:.3f}",
                        "Std": f"{data['std']:.3f}",
                        "CV": f"{data['cv']:.3f}",
                        "Estabilidad": data['stability']
                    })
                
                stability_df = pd.DataFrame(stability_data)
                st.dataframe(stability_df, width='stretch')

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
                            st.plotly_chart(fig, width='stretch', key=f"confusion_matrix_{result_item.model_name.replace(' ', '_')}")
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
                    st.dataframe(pd.DataFrame(perf_data), width='stretch')

            st.divider()

            # Error analysis
            st.container(border=True).markdown("### ⚠️ Análisis de Errores")
            st.info("ℹ️ Este análisis usa predicciones out-of-fold del cross-validation para estimación realista del error.")
            
            X = np.array([features_to_vector(f) for f in dataset])
            y = np.array([f.label for f in dataset])

            # Use out-of-fold predictions if available
            if result.out_of_fold_predictions and result.best_model in result.out_of_fold_predictions:
                y_pred = result.out_of_fold_predictions[result.best_model]
                if y_pred is not None:
                    st.success("✅ Usando predicciones out-of-fold del cross-validation")
                else:
                    st.warning("⚠️ Predicciones out-of-fold son None, usando predicciones in-sample")
                    y_pred = None
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

            # Verify y_pred is not None before proceeding with error analysis
            if y_pred is None:
                st.error("❌ No se pudieron obtener predicciones para el análisis de errores")
                return

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
                st.dataframe(pd.DataFrame(misclassified), width='stretch')
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
            st.dataframe(pd.DataFrame(perf_summary_data), width='stretch')


        st.divider()

        if st.button("🔄 Reentrenar Modelos", type="secondary", width='stretch'):
            del st.session_state.result
            st.rerun()

if __name__ == "__main__":
    main()

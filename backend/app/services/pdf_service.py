"""
Servicio de generación de comprobantes en PDF.

Produce un PDF con la estructura típica de una factura electrónica
peruana (datos del emisor, cliente, detalle, IGV y total) utilizando
reportlab.
"""
import io

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate,
    Table,
    TableStyle,
    Paragraph,
    Spacer,
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

from app.core.config import get_settings
from app.models.invoice import Invoice

settings = get_settings()


def generar_pdf_factura(invoice: Invoice, saldo_pendiente: float) -> bytes:
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        topMargin=15 * mm,
        bottomMargin=15 * mm,
        leftMargin=15 * mm,
        rightMargin=15 * mm,
    )
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle("title", parent=styles["Heading2"], alignment=1)
    small = ParagraphStyle("small", parent=styles["Normal"], fontSize=9)

    elements = []

    encabezado_data = [
        [
            Paragraph(f"<b>{settings.empresa_razon_social}</b><br/>RUC: {settings.empresa_ruc}<br/>{settings.empresa_direccion}", small),
            Paragraph(
                f"<b>FACTURA ELECTRONICA</b><br/>{invoice.serie}-{invoice.numero:06d}",
                title_style,
            ),
        ]
    ]
    tabla_encabezado = Table(encabezado_data, colWidths=[100 * mm, 80 * mm])
    tabla_encabezado.setStyle(
        TableStyle([("BOX", (1, 0), (1, 0), 1, colors.black), ("VALIGN", (0, 0), (-1, -1), "TOP")])
    )
    elements.append(tabla_encabezado)
    elements.append(Spacer(1, 8 * mm))

    cliente_data = [
        ["Cliente:", invoice.client.nombre_razon_social],
        [f"{invoice.client.tipo_documento.value}:", invoice.client.numero_documento],
        ["Fecha de emision:", invoice.fecha_emision.strftime("%d/%m/%Y")],
        ["Fecha de vencimiento:", invoice.fecha_vencimiento.strftime("%d/%m/%Y")],
        ["Estado:", invoice.estado.value.upper()],
    ]
    tabla_cliente = Table(cliente_data, colWidths=[45 * mm, 135 * mm])
    tabla_cliente.setStyle(
        TableStyle(
            [
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ]
        )
    )
    elements.append(tabla_cliente)
    elements.append(Spacer(1, 6 * mm))

    detalle_header = ["Descripcion", "Cantidad", "Precio Unit.", "Subtotal"]
    detalle_rows = [detalle_header]
    for item in invoice.items:
        detalle_rows.append(
            [
                item.descripcion,
                f"{float(item.cantidad):.2f}",
                f"S/ {float(item.precio_unitario):.2f}",
                f"S/ {float(item.subtotal):.2f}",
            ]
        )

    tabla_detalle = Table(detalle_rows, colWidths=[90 * mm, 25 * mm, 30 * mm, 35 * mm])
    tabla_detalle.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1f2937")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
            ]
        )
    )
    elements.append(tabla_detalle)
    elements.append(Spacer(1, 6 * mm))

    totales_data = [
        ["Subtotal:", f"S/ {float(invoice.subtotal):.2f}"],
        ["IGV:", f"S/ {float(invoice.igv):.2f}"],
        ["Total:", f"S/ {float(invoice.total):.2f}"],
        ["Saldo pendiente:", f"S/ {saldo_pendiente:.2f}"],
    ]
    tabla_totales = Table(totales_data, colWidths=[145 * mm, 35 * mm])
    tabla_totales.setStyle(
        TableStyle(
            [
                ("FONTSIZE", (0, 0), (-1, -1), 10),
                ("ALIGN", (1, 0), (1, -1), "RIGHT"),
                ("FONTNAME", (0, 2), (-1, 2), "Helvetica-Bold"),
                ("LINEABOVE", (0, 2), (-1, 2), 0.5, colors.black),
            ]
        )
    )
    elements.append(tabla_totales)

    doc.build(elements)
    buffer.seek(0)
    return buffer.read()

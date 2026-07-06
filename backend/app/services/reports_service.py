"""
Servicio de reportes exportables.

Genera reportes de facturación filtrados por fecha y estado, en
formato Excel (openpyxl) o PDF (reportlab).
"""
import io
from datetime import date
from typing import Optional

from openpyxl import Workbook
from openpyxl.styles import Font
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from sqlalchemy.orm import Session

from app.models.invoice import EstadoFactura
from app.repositories.invoice_repository import InvoiceRepository
from app.services.invoice_service import InvoiceService


class ReportsService:
    def __init__(self, db: Session):
        self.repo = InvoiceRepository(db)
        self.invoice_service = InvoiceService(db)

    def _obtener_facturas(
        self,
        fecha_desde: Optional[date],
        fecha_hasta: Optional[date],
        estado: Optional[EstadoFactura],
    ):
        return self.repo.list(
            estado=estado, fecha_desde=fecha_desde, fecha_hasta=fecha_hasta, skip=0, limit=10_000
        )

    def generar_excel(
        self,
        fecha_desde: Optional[date] = None,
        fecha_hasta: Optional[date] = None,
        estado: Optional[EstadoFactura] = None,
    ) -> bytes:
        facturas = self._obtener_facturas(fecha_desde, fecha_hasta, estado)

        wb = Workbook()
        ws = wb.active
        ws.title = "Reporte de facturacion"

        headers = ["Serie", "Numero", "Cliente", "Documento", "Fecha emision", "Fecha vencimiento", "Subtotal", "IGV", "Total", "Estado", "Dias mora"]
        ws.append(headers)
        for cell in ws[1]:
            cell.font = Font(bold=True)

        for factura in facturas:
            ws.append(
                [
                    factura.serie,
                    factura.numero,
                    factura.client.nombre_razon_social,
                    factura.client.numero_documento,
                    factura.fecha_emision.strftime("%d/%m/%Y"),
                    factura.fecha_vencimiento.strftime("%d/%m/%Y"),
                    float(factura.subtotal),
                    float(factura.igv),
                    float(factura.total),
                    factura.estado.value,
                    self.invoice_service.dias_mora(factura),
                ]
            )

        for column_cells in ws.columns:
            length = max(len(str(cell.value)) if cell.value is not None else 0 for cell in column_cells)
            ws.column_dimensions[column_cells[0].column_letter].width = max(12, length + 2)

        buffer = io.BytesIO()
        wb.save(buffer)
        buffer.seek(0)
        return buffer.read()

    def generar_pdf(
        self,
        fecha_desde: Optional[date] = None,
        fecha_hasta: Optional[date] = None,
        estado: Optional[EstadoFactura] = None,
    ) -> bytes:
        facturas = self._obtener_facturas(fecha_desde, fecha_hasta, estado)
        styles = getSampleStyleSheet()

        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=landscape(A4), topMargin=12 * mm, bottomMargin=12 * mm)
        elements = [Paragraph("Reporte de Facturacion", styles["Heading2"]), Spacer(1, 4 * mm)]

        rango = ""
        if fecha_desde or fecha_hasta:
            rango = f"Periodo: {fecha_desde or '...'} a {fecha_hasta or '...'}"
        if rango:
            elements.append(Paragraph(rango, styles["Normal"]))
            elements.append(Spacer(1, 4 * mm))

        data = [["Serie-Numero", "Cliente", "Emision", "Vencimiento", "Total", "Estado", "Dias mora"]]
        for factura in facturas:
            data.append(
                [
                    f"{factura.serie}-{factura.numero:06d}",
                    factura.client.nombre_razon_social,
                    factura.fecha_emision.strftime("%d/%m/%Y"),
                    factura.fecha_vencimiento.strftime("%d/%m/%Y"),
                    f"S/ {float(factura.total):.2f}",
                    factura.estado.value,
                    str(self.invoice_service.dias_mora(factura)),
                ]
            )

        tabla = Table(data, repeatRows=1)
        tabla.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1f2937")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("FONTSIZE", (0, 0), (-1, -1), 8),
                    ("GRID", (0, 0), (-1, -1), 0.4, colors.grey),
                ]
            )
        )
        elements.append(tabla)
        doc.build(elements)
        buffer.seek(0)
        return buffer.read()

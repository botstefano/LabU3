"""Endpoints de emisión y consulta de facturas, incluyendo descarga de PDF."""
import uuid
from datetime import date
from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models.invoice import EstadoFactura
from app.models.user import User, UserRole
from app.routers.deps import get_current_user, require_roles
from app.schemas.invoice import InvoiceCreate, InvoiceListItem, InvoiceResponse
from app.services.invoice_service import InvoiceService
from app.services.pdf_service import generar_pdf_factura

router = APIRouter(prefix="/api/invoices", tags=["Facturacion"])


def _to_response(invoice, service: InvoiceService) -> InvoiceResponse:
    data = InvoiceResponse.model_validate(invoice)
    data.dias_mora = service.dias_mora(invoice)
    return data


@router.post("", response_model=InvoiceResponse, status_code=201)
def create_invoice(
    data: InvoiceCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMINISTRADOR, UserRole.VENDEDOR, UserRole.CONTADOR)),
):
    service = InvoiceService(db)
    invoice = service.create(data, created_by=current_user.id)
    return _to_response(invoice, service)


@router.get("", response_model=List[InvoiceListItem])
def list_invoices(
    estado: Optional[EstadoFactura] = None,
    fecha_desde: Optional[date] = None,
    fecha_hasta: Optional[date] = None,
    client_id: Optional[uuid.UUID] = None,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    service = InvoiceService(db)
    invoices = service.list(
        estado=estado, fecha_desde=fecha_desde, fecha_hasta=fecha_hasta, client_id=client_id, skip=skip, limit=limit
    )
    result = []
    for inv in invoices:
        result.append(
            InvoiceListItem(
                id=inv.id,
                serie=inv.serie,
                numero=inv.numero,
                fecha_emision=inv.fecha_emision,
                fecha_vencimiento=inv.fecha_vencimiento,
                total=float(inv.total),
                estado=inv.estado,
                cliente_nombre=inv.client.nombre_razon_social,
                dias_mora=service.dias_mora(inv),
            )
        )
    return result


@router.get("/{invoice_id}", response_model=InvoiceResponse)
def get_invoice(
    invoice_id: uuid.UUID,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    service = InvoiceService(db)
    invoice = service.get(invoice_id)
    return _to_response(invoice, service)


@router.post("/{invoice_id}/anular", response_model=InvoiceResponse)
def anular_invoice(
    invoice_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMINISTRADOR, UserRole.CONTADOR)),
):
    service = InvoiceService(db)
    invoice = service.anular(invoice_id)
    return _to_response(invoice, service)


@router.get("/{invoice_id}/pdf")
def descargar_pdf(
    invoice_id: uuid.UUID,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    service = InvoiceService(db)
    invoice = service.get(invoice_id)
    saldo = service.saldo_pendiente(invoice)
    pdf_bytes = generar_pdf_factura(invoice, saldo)
    filename = f"{invoice.serie}-{invoice.numero:06d}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )

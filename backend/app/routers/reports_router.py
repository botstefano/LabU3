"""Endpoints de generación de reportes exportables en PDF y Excel."""
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models.invoice import EstadoFactura
from app.models.user import User
from app.routers.deps import get_current_user
from app.services.reports_service import ReportsService

router = APIRouter(prefix="/api/reports", tags=["Reportes"])


@router.get("/excel")
def reporte_excel(
    fecha_desde: Optional[date] = None,
    fecha_hasta: Optional[date] = None,
    estado: Optional[EstadoFactura] = None,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    contenido = ReportsService(db).generar_excel(fecha_desde, fecha_hasta, estado)
    return Response(
        content=contenido,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": 'attachment; filename="reporte_facturacion.xlsx"'},
    )


@router.get("/pdf")
def reporte_pdf(
    fecha_desde: Optional[date] = None,
    fecha_hasta: Optional[date] = None,
    estado: Optional[EstadoFactura] = None,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    contenido = ReportsService(db).generar_pdf(fecha_desde, fecha_hasta, estado)
    return Response(
        content=contenido,
        media_type="application/pdf",
        headers={"Content-Disposition": 'attachment; filename="reporte_facturacion.pdf"'},
    )

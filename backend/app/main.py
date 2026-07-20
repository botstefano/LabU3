"""
Punto de entrada de la API REST del Sistema de Facturación Electrónica
con Gestión de Cobranzas.

Registra middlewares (CORS), manejador global de excepciones de negocio
y los routers de cada módulo funcional.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.core.exceptions import AppError, app_error_handler
from app.routers import (
    auth_router,
    client_router,
    collections_router,
    dashboard_router,
    invoice_router,
    reports_router,
    settings_router,
    risk_router,
    chat_router,
)

settings = get_settings()

app = FastAPI(
    title="Sistema de Facturacion Electronica con Gestion de Cobranzas",
    description="API REST para emision de comprobantes, gestion de clientes, cobranzas y reportes.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_origin_regex=settings.cors_origin_regex_value,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_exception_handler(AppError, app_error_handler)

print("[MAIN] Including routers...")
print(f"[MAIN] risk_router: {risk_router}")
print(f"[MAIN] risk_router.router: {risk_router.router}")
print(f"[MAIN] risk_router.router prefix: {risk_router.router.prefix}")

app.include_router(auth_router.router)
app.include_router(client_router.router)
app.include_router(invoice_router.router)
app.include_router(collections_router.router)
app.include_router(dashboard_router.router)
app.include_router(reports_router.router)
app.include_router(settings_router.router)
app.include_router(risk_router.router)
print("[MAIN] risk_router included successfully")
app.include_router(chat_router.router)
print("[MAIN] All routers included successfully")


@app.get("/api/health", tags=["Sistema"])
def health_check():
    return {
        "status": "ok", 
        "environment": settings.environment,
        "cors_origins": settings.cors_origins,
        "cors_origins_list": settings.cors_origins_list
    }

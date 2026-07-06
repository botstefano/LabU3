"""
Excepciones de negocio personalizadas y su traducción a respuestas HTTP.

Permite que la capa de servicios lance errores semánticos sin conocer
detalles de FastAPI, manteniendo la separación de responsabilidades.
"""
from fastapi import Request
from fastapi.responses import JSONResponse


class AppError(Exception):
    """Excepción base de la aplicación."""

    status_code = 400

    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


class NotFoundError(AppError):
    status_code = 404


class ConflictError(AppError):
    status_code = 409


class ValidationAppError(AppError):
    status_code = 422


class UnauthorizedError(AppError):
    status_code = 401


class ForbiddenError(AppError):
    status_code = 403


async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.message})

"""
Custom Exception Classes and Error Handlers for SceneIQ
Provides consistent error responses across the API
"""

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
import logging
from datetime import datetime
from typing import Any, Dict

logger = logging.getLogger(__name__)


class SceneIQException(Exception):
    """Base exception for SceneIQ application"""
    
    def __init__(
        self,
        message: str,
        error_code: str = "INTERNAL_ERROR",
        status_code: int = 500,
        details: Dict[str, Any] = None
    ):
        self.message = message
        self.error_code = error_code
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)


class ValidationError(SceneIQException):
    """Raised when request validation fails"""
    
    def __init__(self, message: str, details: Dict[str, Any] = None):
        super().__init__(
            message=message,
            error_code="VALIDATION_ERROR",
            status_code=422,
            details=details
        )


class NotFoundError(SceneIQException):
    """Raised when a resource is not found"""
    
    def __init__(self, resource: str, resource_id: str = None):
        message = f"{resource} not found"
        if resource_id:
            message += f": {resource_id}"
        super().__init__(
            message=message,
            error_code="NOT_FOUND",
            status_code=404
        )


class DatabaseError(SceneIQException):
    """Raised when database operation fails"""
    
    def __init__(self, message: str, details: Dict[str, Any] = None):
        super().__init__(
            message=message,
            error_code="DATABASE_ERROR",
            status_code=500,
            details=details
        )


class UnauthorizedError(SceneIQException):
    """Raised when authentication fails"""
    
    def __init__(self, message: str = "Unauthorized"):
        super().__init__(
            message=message,
            error_code="UNAUTHORIZED",
            status_code=401
        )


class ForbiddenError(SceneIQException):
    """Raised when user lacks permissions"""
    
    def __init__(self, message: str = "Forbidden"):
        super().__init__(
            message=message,
            error_code="FORBIDDEN",
            status_code=403
        )


def error_response(
    message: str,
    error_code: str,
    status_code: int,
    details: Dict[str, Any] = None,
    correlation_id: str = "no-id"
) -> Dict[str, Any]:
    """Format error response"""
    return {
        "error": {
            "message": message,
            "code": error_code,
            "timestamp": datetime.utcnow().isoformat(),
            "correlation_id": correlation_id,
            "details": details or {}
        }
    }


def setup_exception_handlers(app: FastAPI) -> None:
    """Register all exception handlers with the FastAPI app"""
    
    @app.exception_handler(SceneIQException)
    async def pilotforge_exception_handler(request: Request, exc: SceneIQException):
        correlation_id = request.headers.get("X-Correlation-ID", "no-id")
        
        logger.error(
            f"SceneIQException: {exc.message}",
            extra={
                "correlation_id": correlation_id,
                "error_code": exc.error_code,
                "status_code": exc.status_code,
                "details": exc.details,
                "path": request.url.path,
                "method": request.method
            }
        )
        
        return JSONResponse(
            status_code=exc.status_code,
            content=error_response(
                message=exc.message,
                error_code=exc.error_code,
                status_code=exc.status_code,
                details=exc.details,
                correlation_id=correlation_id
            )
        )
    
    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        correlation_id = request.headers.get("X-Correlation-ID", "no-id")
        
        logger.warning(
            "Request validation failed",
            extra={
                "correlation_id": correlation_id,
                "errors": exc.errors(),
                "path": request.url.path,
                "method": request.method
            }
        )
        
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content=error_response(
                message="Request validation failed",
                error_code="VALIDATION_ERROR",
                status_code=422,
                details={"errors": exc.errors()},
                correlation_id=correlation_id
            )
        )
    
    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException):
        correlation_id = request.headers.get("X-Correlation-ID", "no-id")
        
        logger.warning(
            f"HTTP Exception: {exc.detail}",
            extra={
                "correlation_id": correlation_id,
                "status_code": exc.status_code,
                "path": request.url.path,
                "method": request.method
            }
        )
        
        return JSONResponse(
            status_code=exc.status_code,
            content=error_response(
                message=exc.detail,
                error_code="HTTP_ERROR",
                status_code=exc.status_code,
                correlation_id=correlation_id
            )
        )
    
    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        correlation_id = request.headers.get("X-Correlation-ID", "no-id")
        
        logger.error(
            f"Unhandled exception: {str(exc)}",
            extra={
                "correlation_id": correlation_id,
                "exception_type": type(exc).__name__,
                "path": request.url.path,
                "method": request.method
            },
            exc_info=True
        )
        
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=error_response(
                message="Internal server error",
                error_code="INTERNAL_ERROR",
                status_code=500,
                correlation_id=correlation_id
            )
        )



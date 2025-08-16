"""
Global error handlers for FastAPI application
"""
import traceback
from typing import Dict, Any
from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from sqlalchemy.exc import SQLAlchemyError
from pydantic import ValidationError

from app.core.exceptions import (
    BusinessDirectoryException,
    BusinessDirectoryHTTPException,
    ScrapingException,
    GeocodingException,
    DatabaseException,
    ErrorCodes
)
from config.logging import get_api_logger, get_correlation_id

logger = get_api_logger()


def create_error_response(
    status_code: int,
    message: str,
    error_code: str = None,
    details: Dict[str, Any] = None,
    correlation_id: str = None
) -> JSONResponse:
    """Create standardized error response"""
    
    error_response = {
        "error": {
            "message": message,
            "error_code": error_code,
            "status_code": status_code,
            "correlation_id": correlation_id or get_correlation_id(),
            "details": details or {}
        }
    }
    
    return JSONResponse(
        status_code=status_code,
        content=error_response
    )


async def business_directory_exception_handler(request: Request, exc: BusinessDirectoryException) -> JSONResponse:
    """Handle custom business directory exceptions"""
    
    correlation_id = get_correlation_id()
    
    # Log the exception
    logger.error(
        f"Business directory exception: {exc.message}",
        extra={
            "extra_fields": {
                "exception_type": type(exc).__name__,
                "message": exc.message,
                "details": exc.details,
                "correlation_id": correlation_id,
                "path": request.url.path,
                "method": request.method,
                "event_type": "business_directory_exception"
            }
        },
        exc_info=True
    )
    
    # Map exception types to HTTP status codes
    if isinstance(exc, ScrapingException):
        status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        error_code = ErrorCodes.SCRAPING_FAILED
    elif isinstance(exc, GeocodingException):
        status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        error_code = ErrorCodes.GEOCODING_FAILED
    elif isinstance(exc, DatabaseException):
        status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        error_code = ErrorCodes.DATABASE_QUERY_ERROR
    else:
        status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        error_code = ErrorCodes.INTERNAL_ERROR
    
    return create_error_response(
        status_code=status_code,
        message=exc.message,
        error_code=error_code,
        details=exc.details,
        correlation_id=correlation_id
    )


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """Handle HTTP exceptions"""
    
    correlation_id = get_correlation_id()
    
    # Handle custom HTTP exceptions
    if isinstance(exc, BusinessDirectoryHTTPException):
        logger.warning(
            f"HTTP exception: {exc.detail['message']}",
            extra={
                "extra_fields": {
                    "status_code": exc.status_code,
                    "error_code": exc.error_code,
                    "details": exc.details,
                    "correlation_id": correlation_id,
                    "path": request.url.path,
                    "method": request.method,
                    "event_type": "http_exception"
                }
            }
        )
        
        return create_error_response(
            status_code=exc.status_code,
            message=exc.detail["message"],
            error_code=exc.error_code,
            details=exc.details,
            correlation_id=correlation_id
        )
    
    # Handle standard HTTP exceptions
    logger.warning(
        f"HTTP exception: {exc.detail}",
        extra={
            "extra_fields": {
                "status_code": exc.status_code,
                "detail": exc.detail,
                "correlation_id": correlation_id,
                "path": request.url.path,
                "method": request.method,
                "event_type": "http_exception"
            }
        }
    )
    
    return create_error_response(
        status_code=exc.status_code,
        message=str(exc.detail),
        correlation_id=correlation_id
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Handle request validation errors"""
    
    correlation_id = get_correlation_id()
    
    # Extract validation error details
    validation_errors = []
    for error in exc.errors():
        validation_errors.append({
            "field": " -> ".join(str(loc) for loc in error["loc"]),
            "message": error["msg"],
            "type": error["type"],
            "input": error.get("input")
        })
    
    logger.warning(
        f"Validation error: {len(validation_errors)} field(s) failed validation",
        extra={
            "extra_fields": {
                "validation_errors": validation_errors,
                "correlation_id": correlation_id,
                "path": request.url.path,
                "method": request.method,
                "event_type": "validation_error"
            }
        }
    )
    
    return create_error_response(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        message="Request validation failed",
        error_code=ErrorCodes.VALIDATION_ERROR,
        details={"validation_errors": validation_errors},
        correlation_id=correlation_id
    )


async def sqlalchemy_exception_handler(request: Request, exc: SQLAlchemyError) -> JSONResponse:
    """Handle SQLAlchemy database errors"""
    
    correlation_id = get_correlation_id()
    
    logger.error(
        f"Database error: {str(exc)}",
        extra={
            "extra_fields": {
                "exception_type": type(exc).__name__,
                "error": str(exc),
                "correlation_id": correlation_id,
                "path": request.url.path,
                "method": request.method,
                "event_type": "database_error"
            }
        },
        exc_info=True
    )
    
    return create_error_response(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        message="Database operation failed",
        error_code=ErrorCodes.DATABASE_QUERY_ERROR,
        details={"database_error": str(exc)},
        correlation_id=correlation_id
    )


async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle all other unhandled exceptions"""
    
    correlation_id = get_correlation_id()
    
    # Get traceback for debugging
    tb_str = traceback.format_exc()
    
    logger.error(
        f"Unhandled exception: {str(exc)}",
        extra={
            "extra_fields": {
                "exception_type": type(exc).__name__,
                "error": str(exc),
                "traceback": tb_str,
                "correlation_id": correlation_id,
                "path": request.url.path,
                "method": request.method,
                "event_type": "unhandled_exception"
            }
        },
        exc_info=True
    )
    
    return create_error_response(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        message="An unexpected error occurred",
        error_code=ErrorCodes.INTERNAL_ERROR,
        details={"exception_type": type(exc).__name__},
        correlation_id=correlation_id
    )


def register_exception_handlers(app):
    """Register all exception handlers with the FastAPI app"""
    
    app.add_exception_handler(BusinessDirectoryException, business_directory_exception_handler)
    app.add_exception_handler(BusinessDirectoryHTTPException, http_exception_handler)
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(SQLAlchemyError, sqlalchemy_exception_handler)
    app.add_exception_handler(Exception, general_exception_handler)
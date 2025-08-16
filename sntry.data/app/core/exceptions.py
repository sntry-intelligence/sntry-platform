"""
Custom exceptions and error handling for the Jamaica Business Directory
"""
from typing import Any, Dict, Optional
from fastapi import HTTPException, status


class BusinessDirectoryException(Exception):
    """Base exception for business directory operations"""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        self.message = message
        self.details = details or {}
        super().__init__(self.message)


class ScrapingException(BusinessDirectoryException):
    """Exception for scraping-related errors"""
    pass


class AntiBot Exception(ScrapingException):
    """Exception for anti-bot detection"""
    pass


class GeocodingException(BusinessDirectoryException):
    """Exception for geocoding-related errors"""
    pass


class GeocodingQuotaExceededException(GeocodingException):
    """Exception for geocoding quota exceeded"""
    pass


class DatabaseException(BusinessDirectoryException):
    """Exception for database-related errors"""
    pass


class ValidationException(BusinessDirectoryException):
    """Exception for data validation errors"""
    pass


class ExternalAPIException(BusinessDirectoryException):
    """Exception for external API errors"""
    pass


class ConfigurationException(BusinessDirectoryException):
    """Exception for configuration errors"""
    pass


# HTTP Exception classes for API responses
class BusinessDirectoryHTTPException(HTTPException):
    """Base HTTP exception with structured error response"""
    
    def __init__(
        self,
        status_code: int,
        message: str,
        error_code: str = None,
        details: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None
    ):
        self.error_code = error_code
        self.details = details or {}
        
        detail = {
            "message": message,
            "error_code": error_code,
            "details": self.details
        }
        
        super().__init__(status_code=status_code, detail=detail, headers=headers)


class BadRequestException(BusinessDirectoryHTTPException):
    """400 Bad Request"""
    
    def __init__(self, message: str = "Bad request", **kwargs):
        super().__init__(status_code=status.HTTP_400_BAD_REQUEST, message=message, **kwargs)


class UnauthorizedException(BusinessDirectoryHTTPException):
    """401 Unauthorized"""
    
    def __init__(self, message: str = "Unauthorized", **kwargs):
        super().__init__(status_code=status.HTTP_401_UNAUTHORIZED, message=message, **kwargs)


class ForbiddenException(BusinessDirectoryHTTPException):
    """403 Forbidden"""
    
    def __init__(self, message: str = "Forbidden", **kwargs):
        super().__init__(status_code=status.HTTP_403_FORBIDDEN, message=message, **kwargs)


class NotFoundException(BusinessDirectoryHTTPException):
    """404 Not Found"""
    
    def __init__(self, message: str = "Resource not found", **kwargs):
        super().__init__(status_code=status.HTTP_404_NOT_FOUND, message=message, **kwargs)


class ConflictException(BusinessDirectoryHTTPException):
    """409 Conflict"""
    
    def __init__(self, message: str = "Resource conflict", **kwargs):
        super().__init__(status_code=status.HTTP_409_CONFLICT, message=message, **kwargs)


class UnprocessableEntityException(BusinessDirectoryHTTPException):
    """422 Unprocessable Entity"""
    
    def __init__(self, message: str = "Unprocessable entity", **kwargs):
        super().__init__(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, message=message, **kwargs)


class TooManyRequestsException(BusinessDirectoryHTTPException):
    """429 Too Many Requests"""
    
    def __init__(self, message: str = "Too many requests", retry_after: int = None, **kwargs):
        headers = {"Retry-After": str(retry_after)} if retry_after else None
        super().__init__(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            message=message,
            headers=headers,
            **kwargs
        )


class InternalServerErrorException(BusinessDirectoryHTTPException):
    """500 Internal Server Error"""
    
    def __init__(self, message: str = "Internal server error", **kwargs):
        super().__init__(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, message=message, **kwargs)


class ServiceUnavailableException(BusinessDirectoryHTTPException):
    """503 Service Unavailable"""
    
    def __init__(self, message: str = "Service unavailable", retry_after: int = None, **kwargs):
        headers = {"Retry-After": str(retry_after)} if retry_after else None
        super().__init__(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            message=message,
            headers=headers,
            **kwargs
        )


# Error code constants
class ErrorCodes:
    """Standard error codes for the application"""
    
    # General errors
    VALIDATION_ERROR = "VALIDATION_ERROR"
    CONFIGURATION_ERROR = "CONFIGURATION_ERROR"
    INTERNAL_ERROR = "INTERNAL_ERROR"
    
    # Database errors
    DATABASE_CONNECTION_ERROR = "DATABASE_CONNECTION_ERROR"
    DATABASE_QUERY_ERROR = "DATABASE_QUERY_ERROR"
    RECORD_NOT_FOUND = "RECORD_NOT_FOUND"
    DUPLICATE_RECORD = "DUPLICATE_RECORD"
    
    # Scraping errors
    SCRAPING_FAILED = "SCRAPING_FAILED"
    ANTI_BOT_DETECTED = "ANTI_BOT_DETECTED"
    SCRAPING_TIMEOUT = "SCRAPING_TIMEOUT"
    INVALID_SCRAPING_TARGET = "INVALID_SCRAPING_TARGET"
    
    # Geocoding errors
    GEOCODING_FAILED = "GEOCODING_FAILED"
    GEOCODING_QUOTA_EXCEEDED = "GEOCODING_QUOTA_EXCEEDED"
    INVALID_ADDRESS = "INVALID_ADDRESS"
    GEOCODING_API_ERROR = "GEOCODING_API_ERROR"
    
    # External API errors
    EXTERNAL_API_ERROR = "EXTERNAL_API_ERROR"
    API_QUOTA_EXCEEDED = "API_QUOTA_EXCEEDED"
    API_TIMEOUT = "API_TIMEOUT"
    
    # Task errors
    TASK_FAILED = "TASK_FAILED"
    TASK_TIMEOUT = "TASK_TIMEOUT"
    TASK_NOT_FOUND = "TASK_NOT_FOUND"
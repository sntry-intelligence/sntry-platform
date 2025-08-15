import structlog
import logging
import sys
from typing import Any, Dict
from shared.config import get_settings

settings = get_settings()


def configure_logging():
    """Configure structured logging"""
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, settings.log_level.upper()),
    )

    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer()
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )


def get_logger(name: str) -> structlog.BoundLogger:
    """Get a structured logger instance"""
    return structlog.get_logger(name)


class RequestLogger:
    """Request logging middleware"""
    
    def __init__(self, logger_name: str = "api"):
        self.logger = get_logger(logger_name)
    
    async def log_request(self, request_id: str, method: str, path: str, **kwargs):
        """Log incoming request"""
        self.logger.info(
            "Request received",
            request_id=request_id,
            method=method,
            path=path,
            **kwargs
        )
    
    async def log_response(self, request_id: str, status_code: int, duration_ms: float, **kwargs):
        """Log outgoing response"""
        self.logger.info(
            "Request completed",
            request_id=request_id,
            status_code=status_code,
            duration_ms=duration_ms,
            **kwargs
        )
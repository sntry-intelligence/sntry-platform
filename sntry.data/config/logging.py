"""
Logging configuration with structured JSON formatting and correlation IDs
"""
import logging
import logging.config
import json
import uuid
from pathlib import Path
from contextvars import ContextVar
from typing import Optional

# Create logs directory if it doesn't exist
logs_dir = Path("logs")
logs_dir.mkdir(exist_ok=True)

# Context variable for correlation ID
correlation_id: ContextVar[Optional[str]] = ContextVar('correlation_id', default=None)

class CorrelationIdFilter(logging.Filter):
    """Add correlation ID to log records"""
    
    def filter(self, record):
        record.correlation_id = correlation_id.get() or "N/A"
        return True


class StructuredFormatter(logging.Formatter):
    """Custom JSON formatter with structured fields"""
    
    def format(self, record):
        log_entry = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "logger": record.name,
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
            "message": record.getMessage(),
            "correlation_id": getattr(record, 'correlation_id', 'N/A'),
        }
        
        # Add extra fields if present
        if hasattr(record, 'extra_fields'):
            log_entry.update(record.extra_fields)
            
        # Add exception info if present
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)
            
        return json.dumps(log_entry, default=str)


LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "default": {
            "format": "%(asctime)s - %(name)s - %(levelname)s - %(correlation_id)s - %(message)s",
            "datefmt": "%Y-%m-%d %H:%M:%S",
        },
        "detailed": {
            "format": "%(asctime)s - %(name)s - %(levelname)s - %(module)s - %(funcName)s - %(lineno)d - %(correlation_id)s - %(message)s",
            "datefmt": "%Y-%m-%d %H:%M:%S",
        },
        "json": {
            "()": StructuredFormatter,
            "datefmt": "%Y-%m-%d %H:%M:%S"
        }
    },
    "filters": {
        "correlation_id": {
            "()": CorrelationIdFilter,
        }
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "level": "INFO",
            "formatter": "default",
            "stream": "ext://sys.stdout",
            "filters": ["correlation_id"],
        },
        "file": {
            "class": "logging.handlers.RotatingFileHandler",
            "level": "DEBUG",
            "formatter": "json",
            "filename": "logs/app.log",
            "maxBytes": 10485760,  # 10MB
            "backupCount": 5,
            "filters": ["correlation_id"],
        },
        "error_file": {
            "class": "logging.handlers.RotatingFileHandler",
            "level": "ERROR",
            "formatter": "json",
            "filename": "logs/error.log",
            "maxBytes": 10485760,  # 10MB
            "backupCount": 5,
            "filters": ["correlation_id"],
        },
        "scraping_file": {
            "class": "logging.handlers.RotatingFileHandler",
            "level": "INFO",
            "formatter": "json",
            "filename": "logs/scraping.log",
            "maxBytes": 10485760,  # 10MB
            "backupCount": 5,
            "filters": ["correlation_id"],
        },
        "geocoding_file": {
            "class": "logging.handlers.RotatingFileHandler",
            "level": "INFO",
            "formatter": "json",
            "filename": "logs/geocoding.log",
            "maxBytes": 10485760,  # 10MB
            "backupCount": 5,
            "filters": ["correlation_id"],
        },
        "api_file": {
            "class": "logging.handlers.RotatingFileHandler",
            "level": "INFO",
            "formatter": "json",
            "filename": "logs/api.log",
            "maxBytes": 10485760,  # 10MB
            "backupCount": 5,
            "filters": ["correlation_id"],
        },
        "celery_file": {
            "class": "logging.handlers.RotatingFileHandler",
            "level": "INFO",
            "formatter": "json",
            "filename": "logs/celery.log",
            "maxBytes": 10485760,  # 10MB
            "backupCount": 5,
            "filters": ["correlation_id"],
        },
    },
    "loggers": {
        "": {  # root logger
            "level": "INFO",
            "handlers": ["console", "file", "error_file"],
        },
        "app": {
            "level": "DEBUG",
            "handlers": ["console", "file"],
            "propagate": False,
        },
        "app.api": {
            "level": "INFO",
            "handlers": ["console", "api_file"],
            "propagate": False,
        },
        "app.scraping": {
            "level": "INFO",
            "handlers": ["console", "scraping_file"],
            "propagate": False,
        },
        "app.geocoding": {
            "level": "INFO",
            "handlers": ["console", "geocoding_file"],
            "propagate": False,
        },
        "celery": {
            "level": "INFO",
            "handlers": ["console", "celery_file"],
            "propagate": False,
        },
        "sqlalchemy.engine": {
            "level": "WARNING",
            "handlers": ["file"],
            "propagate": False,
        },
        "uvicorn": {
            "level": "INFO",
            "handlers": ["console", "file"],
            "propagate": False,
        },
        "uvicorn.access": {
            "level": "INFO",
            "handlers": ["api_file"],
            "propagate": False,
        },
    },
}


def setup_logging():
    """Setup logging configuration"""
    logging.config.dictConfig(LOGGING_CONFIG)


def set_correlation_id(cid: Optional[str] = None) -> str:
    """Set correlation ID for current context"""
    if cid is None:
        cid = str(uuid.uuid4())
    correlation_id.set(cid)
    return cid


def get_correlation_id() -> Optional[str]:
    """Get current correlation ID"""
    return correlation_id.get()


def get_logger(name: str) -> logging.Logger:
    """Get logger with structured logging capabilities"""
    return logging.getLogger(name)


def log_with_extra(logger: logging.Logger, level: int, message: str, **extra_fields):
    """Log message with extra structured fields"""
    record = logger.makeRecord(
        logger.name, level, "", 0, message, (), None
    )
    record.extra_fields = extra_fields
    logger.handle(record)


# Specialized loggers for different components
def get_api_logger() -> logging.Logger:
    """Get API-specific logger"""
    return logging.getLogger("app.api")


def get_scraping_logger() -> logging.Logger:
    """Get scraping-specific logger"""
    return logging.getLogger("app.scraping")


def get_geocoding_logger() -> logging.Logger:
    """Get geocoding-specific logger"""
    return logging.getLogger("app.geocoding")
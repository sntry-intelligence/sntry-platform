"""
Database configuration and session management for guardrails service
"""
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from .models import Base, GuardrailsConfig

# Database configuration
DATABASE_URL = os.getenv(
    "GUARDRAILS_DATABASE_URL",
    "postgresql://postgres:password@localhost:5432/guardrails_db"
)

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Session:
    """Dependency to get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_tables():
    """Create all database tables"""
    Base.metadata.create_all(bind=engine)


def init_default_configs(db: Session):
    """Initialize default guardrails configurations"""
    
    default_configs = [
        {
            "name": "default_content_moderation",
            "description": "Default content moderation policy",
            "config_data": {
                "enabled_checks": [
                    "toxicity", "hate_speech", "violence", "profanity", "pii"
                ],
                "severity_thresholds": {
                    "toxicity": 0.7,
                    "hate_speech": 0.6,
                    "violence": 0.8,
                    "profanity": 0.5,
                    "pii": 0.9
                },
                "actions": {
                    "low": "allow",
                    "medium": "warn",
                    "high": "filter",
                    "critical": "block"
                }
            }
        },
        {
            "name": "strict_content_moderation",
            "description": "Strict content moderation for sensitive applications",
            "config_data": {
                "enabled_checks": [
                    "toxicity", "hate_speech", "violence", "profanity", "pii", "bias"
                ],
                "severity_thresholds": {
                    "toxicity": 0.5,
                    "hate_speech": 0.4,
                    "violence": 0.6,
                    "profanity": 0.3,
                    "pii": 0.8,
                    "bias": 0.6
                },
                "actions": {
                    "low": "warn",
                    "medium": "filter",
                    "high": "block",
                    "critical": "block"
                }
            }
        },
        {
            "name": "permissive_content_moderation",
            "description": "Permissive content moderation for creative applications",
            "config_data": {
                "enabled_checks": [
                    "hate_speech", "violence", "pii"
                ],
                "severity_thresholds": {
                    "hate_speech": 0.8,
                    "violence": 0.9,
                    "pii": 0.95
                },
                "actions": {
                    "low": "allow",
                    "medium": "allow",
                    "high": "warn",
                    "critical": "filter"
                }
            }
        },
        {
            "name": "bias_detection_standard",
            "description": "Standard bias detection configuration",
            "config_data": {
                "enabled_bias_types": [
                    "gender", "racial", "age", "religious"
                ],
                "bias_thresholds": {
                    "gender": 0.6,
                    "racial": 0.5,
                    "age": 0.7,
                    "religious": 0.6
                },
                "action_on_bias": "warn"
            }
        },
        {
            "name": "response_validation_comprehensive",
            "description": "Comprehensive response validation rules",
            "config_data": {
                "validation_rules": [
                    "no_personal_info",
                    "max_length_2000",
                    "relevance_check"
                ],
                "require_all_pass": False,
                "min_confidence": 0.7
            }
        }
    ]
    
    for config_data in default_configs:
        existing_config = db.query(GuardrailsConfig).filter(
            GuardrailsConfig.name == config_data["name"]
        ).first()
        
        if not existing_config:
            config = GuardrailsConfig(**config_data)
            db.add(config)
    
    db.commit()


def initialize_database():
    """Initialize database with tables and default configurations"""
    create_tables()
    
    db = SessionLocal()
    try:
        init_default_configs(db)
        print("Guardrails database initialized successfully!")
    finally:
        db.close()


if __name__ == "__main__":
    initialize_database()
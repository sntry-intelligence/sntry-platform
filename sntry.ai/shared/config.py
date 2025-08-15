from functools import lru_cache
from typing import Optional
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings"""
    
    # Database
    database_url: str = "postgresql://sntry_user:sntry_password@localhost:5432/sntry_ai"
    redis_url: str = "redis://localhost:6379"
    
    # API Configuration
    api_title: str = "sntry.app/ai/v1 API"
    api_version: str = "1.0.0"
    api_description: str = "REST API Development Framework for Agentic Workflows"
    
    # Security
    secret_key: str = "your-secret-key-change-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    
    # JWT Authentication
    jwt_secret_key: str = "your-jwt-secret-key-change-in-production"
    JWT_SECRET_KEY: str = "your-jwt-secret-key-change-in-production"  # Alias for compatibility
    
    # OAuth 2.0 Configuration
    oauth_token_url: str = "https://oauth.example.com/token"
    oauth_userinfo_url: str = "https://oauth.example.com/userinfo"
    oauth_client_id: str = "your-oauth-client-id"
    oauth_client_secret: str = "your-oauth-client-secret"
    
    # HTTPS Configuration
    enforce_https: bool = True
    allowed_hosts: list[str] = ["localhost", "127.0.0.1", "*.sntry.app"]
    
    # Google Cloud
    google_cloud_project: Optional[str] = None
    google_application_credentials: Optional[str] = None
    vertex_ai_location: str = "us-central1"
    
    # Vector Databases
    pinecone_api_key: Optional[str] = None
    pinecone_environment: Optional[str] = None
    weaviate_url: Optional[str] = None
    weaviate_api_key: Optional[str] = None
    qdrant_url: Optional[str] = None
    qdrant_api_key: Optional[str] = None
    
    # Service URLs (for inter-service communication)
    agent_management_url: str = "http://localhost:8001"
    workflow_orchestration_url: str = "http://localhost:8002"
    tool_management_url: str = "http://localhost:8003"
    vector_database_url: str = "http://localhost:8004"
    mcp_integration_url: str = "http://localhost:8005"
    
    # Monitoring and Observability
    log_level: str = "INFO"
    enable_metrics: bool = True
    enable_tracing: bool = True
    
    # Rate Limiting
    rate_limit_requests: int = 100
    rate_limit_window: int = 60  # seconds
    
    class Config:
        env_file = ".env"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()
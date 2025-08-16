"""
Application configuration management using Pydantic Settings
"""
from typing import List, Optional
from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings with environment variable support"""
    
    # Application settings
    APP_NAME: str = "Jamaica Business Directory"
    ENVIRONMENT: str = Field(default="development", description="Environment: development, staging, production")
    DEBUG: bool = Field(default=True, description="Debug mode")
    ALLOWED_HOSTS: List[str] = Field(default=["*"], description="Allowed CORS origins")
    
    # Database settings - PostgreSQL
    POSTGRES_HOST: str = Field(default="localhost", description="PostgreSQL host")
    POSTGRES_PORT: int = Field(default=5432, description="PostgreSQL port")
    POSTGRES_DB: str = Field(default="jamaica_business_db", description="PostgreSQL database name")
    POSTGRES_USER: str = Field(default="postgres", description="PostgreSQL username")
    POSTGRES_PASSWORD: str = Field(default="postgres", description="PostgreSQL password")
    
    @property
    def postgres_url(self) -> str:
        """PostgreSQL connection URL"""
        return f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
    
    # SQL Server settings - Data Warehouse
    SQLSERVER_HOST: str = Field(default="localhost", description="SQL Server host")
    SQLSERVER_PORT: int = Field(default=1433, description="SQL Server port")
    SQLSERVER_DB: str = Field(default="CustomerDataWarehouse", description="SQL Server database name")
    SQLSERVER_USER: str = Field(default="sa", description="SQL Server username")
    SQLSERVER_PASSWORD: str = Field(default="", description="SQL Server password")
    
    @property
    def sqlserver_url(self) -> str:
        """SQL Server connection URL"""
        return f"mssql+pyodbc://{self.SQLSERVER_USER}:{self.SQLSERVER_PASSWORD}@{self.SQLSERVER_HOST}:{self.SQLSERVER_PORT}/{self.SQLSERVER_DB}?driver=ODBC+Driver+17+for+SQL+Server"
    
    # Redis settings
    REDIS_HOST: str = Field(default="localhost", description="Redis host")
    REDIS_PORT: int = Field(default=6379, description="Redis port")
    REDIS_DB: int = Field(default=0, description="Redis database number")
    REDIS_PASSWORD: Optional[str] = Field(default=None, description="Redis password")
    
    @property
    def redis_url(self) -> str:
        """Redis connection URL"""
        if self.REDIS_PASSWORD:
            return f"redis://:{self.REDIS_PASSWORD}@{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"
    
    # Kafka settings
    KAFKA_BOOTSTRAP_SERVERS: List[str] = Field(default=["localhost:9092"], description="Kafka bootstrap servers")
    KAFKA_CONSUMER_GROUP: str = Field(default="jamaica-business-directory", description="Kafka consumer group")
    
    # Google APIs
    GOOGLE_MAPS_API_KEY: str = Field(default="", description="Google Maps API key")
    GOOGLE_GEOCODING_API_KEY: str = Field(default="", description="Google Geocoding API key")
    
    # Celery settings
    CELERY_BROKER_URL: str = Field(default="redis://localhost:6379/1", description="Celery broker URL")
    CELERY_RESULT_BACKEND: str = Field(default="redis://localhost:6379/2", description="Celery result backend")
    CELERY_TASK_TIME_LIMIT: int = Field(default=1800, description="Task time limit in seconds (30 minutes)")
    CELERY_TASK_SOFT_TIME_LIMIT: int = Field(default=1500, description="Task soft time limit in seconds (25 minutes)")
    CELERY_WORKER_PREFETCH_MULTIPLIER: int = Field(default=1, description="Worker prefetch multiplier")
    CELERY_MAX_RETRIES: int = Field(default=3, description="Maximum task retries")
    CELERY_RETRY_DELAY: int = Field(default=60, description="Base retry delay in seconds")
    
    @property
    def celery_broker_url(self) -> str:
        """Celery broker URL using Redis settings"""
        if self.REDIS_PASSWORD:
            return f"redis://:{self.REDIS_PASSWORD}@{self.REDIS_HOST}:{self.REDIS_PORT}/1"
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/1"
    
    @property
    def celery_result_backend(self) -> str:
        """Celery result backend URL using Redis settings"""
        if self.REDIS_PASSWORD:
            return f"redis://:{self.REDIS_PASSWORD}@{self.REDIS_HOST}:{self.REDIS_PORT}/2"
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/2"
    
    # Scraping settings
    SCRAPING_DELAY_MIN: float = Field(default=1.0, description="Minimum delay between requests (seconds)")
    SCRAPING_DELAY_MAX: float = Field(default=3.0, description="Maximum delay between requests (seconds)")
    SCRAPING_USER_AGENTS: List[str] = Field(
        default=[
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        ],
        description="User agents for web scraping"
    )
    
    # Alerting and monitoring settings
    SMTP_HOST: Optional[str] = Field(default=None, description="SMTP server host for email alerts")
    SMTP_PORT: int = Field(default=587, description="SMTP server port")
    SMTP_USE_TLS: bool = Field(default=True, description="Use TLS for SMTP")
    SMTP_USERNAME: Optional[str] = Field(default=None, description="SMTP username")
    SMTP_PASSWORD: Optional[str] = Field(default=None, description="SMTP password")
    SMTP_FROM_EMAIL: str = Field(default="alerts@jamaica-business-directory.com", description="From email address for alerts")
    ALERT_EMAIL_RECIPIENTS: List[str] = Field(default=[], description="Email recipients for alerts")
    
    # Performance monitoring thresholds
    PERFORMANCE_RESPONSE_TIME_THRESHOLD_MS: int = Field(default=2000, description="Response time threshold in milliseconds")
    PERFORMANCE_CPU_THRESHOLD_PERCENT: int = Field(default=80, description="CPU usage threshold percentage")
    PERFORMANCE_MEMORY_THRESHOLD_PERCENT: int = Field(default=85, description="Memory usage threshold percentage")
    PERFORMANCE_DISK_THRESHOLD_PERCENT: int = Field(default=90, description="Disk usage threshold percentage")
    
    # Cost monitoring
    GEOCODING_MONTHLY_BUDGET_USD: float = Field(default=100.0, description="Monthly budget for geocoding API in USD")
    GEOCODING_DAILY_BUDGET_USD: float = Field(default=10.0, description="Daily budget for geocoding API in USD")
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
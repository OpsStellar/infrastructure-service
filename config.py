"""
Configuration settings for Infrastructure Service
"""

import os
from typing import Optional
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings"""
    
    # Service Configuration
    SERVICE_NAME: str = "infrastructure-service"
    SERVICE_VERSION: str = "1.0.0"
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    
    # Database
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "sqlite:///./infrastructure.db"
    )
    
    # Redis Cache
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    CACHE_TTL: int = int(os.getenv("CACHE_TTL", "300"))
    
    # Service URLs
    AUTH_SERVICE_URL: str = os.getenv("AUTH_SERVICE_URL", "http://auth-service:8001")
    SETTINGS_SERVICE_URL: str = os.getenv("SETTINGS_SERVICE_URL", "http://settings-service:8020")
    COST_SERVICE_URL: str = os.getenv("COST_SERVICE_URL", "http://cost-service:8010")
    
    # OpenTelemetry
    OTEL_EXPORTER_OTLP_ENDPOINT: str = os.getenv(
        "OTEL_EXPORTER_OTLP_ENDPOINT",
        "http://localhost:4317"
    )
    OTEL_SERVICE_NAME: str = SERVICE_NAME
    
    # IaC Provider Settings
    TERRAFORM_ENABLED: bool = os.getenv("ENABLE_TERRAFORM", "true").lower() == "true"
    CLOUDFORMATION_ENABLED: bool = os.getenv("ENABLE_CLOUDFORMATION", "true").lower() == "true"
    ARM_ENABLED: bool = os.getenv("ENABLE_ARM", "true").lower() == "true"
    GCP_DEPLOYMENT_ENABLED: bool = os.getenv("ENABLE_GCP_DEPLOYMENT", "true").lower() == "true"
    
    # AWS Configuration
    AWS_REGION: Optional[str] = os.getenv("AWS_REGION", "us-east-1")
    AWS_ACCESS_KEY_ID: Optional[str] = os.getenv("AWS_ACCESS_KEY_ID")
    AWS_SECRET_ACCESS_KEY: Optional[str] = os.getenv("AWS_SECRET_ACCESS_KEY")
    
    # Azure Configuration
    AZURE_SUBSCRIPTION_ID: Optional[str] = os.getenv("AZURE_SUBSCRIPTION_ID")
    AZURE_TENANT_ID: Optional[str] = os.getenv("AZURE_TENANT_ID")
    AZURE_CLIENT_ID: Optional[str] = os.getenv("AZURE_CLIENT_ID")
    AZURE_CLIENT_SECRET: Optional[str] = os.getenv("AZURE_CLIENT_SECRET")
    
    # GCP Configuration
    GCP_PROJECT_ID: Optional[str] = os.getenv("GCP_PROJECT_ID")
    GCP_SERVICE_ACCOUNT_KEY: Optional[str] = os.getenv("GCP_SERVICE_ACCOUNT_KEY")
    
    # Drift Detection
    DRIFT_CHECK_INTERVAL_HOURS: int = int(os.getenv("DRIFT_CHECK_INTERVAL_HOURS", "24"))
    
    # Resource Sync
    RESOURCE_SYNC_INTERVAL_MINUTES: int = int(os.getenv("RESOURCE_SYNC_INTERVAL_MINUTES", "30"))
    
    class Config:
        case_sensitive = True
        env_file = ".env"


# Global settings instance
settings = Settings()

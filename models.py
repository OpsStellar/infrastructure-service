"""
Database models for Infrastructure Service
"""

from sqlalchemy import Column, String, Integer, Float, Boolean, DateTime, JSON, Text
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()


class InfrastructureStack(Base):
    """Infrastructure stack model"""
    __tablename__ = "infrastructure_stacks"

    id = Column(String(36), primary_key=True)
    name = Column(String(255), nullable=False, index=True)
    provider = Column(String(50), nullable=False)  # terraform, cloudformation, arm, gcp_deployment
    cloud_provider = Column(String(50), nullable=False, index=True)  # aws, azure, gcp
    environment = Column(String(50), nullable=False, index=True)
    region = Column(String(100), nullable=False)
    status = Column(String(50), nullable=False, index=True)
    description = Column(Text, nullable=True)
    
    # Repository information
    repository_url = Column(String(500), nullable=True)
    branch = Column(String(100), default="main")
    path = Column(String(500), default="/")
    
    # Configuration
    variables = Column(JSON, default={})
    tags = Column(JSON, default={})
    
    # Resource tracking
    resource_count = Column(Integer, default=0)
    
    # Drift detection
    drift_status = Column(String(50), default="no_drift")
    last_drift_check = Column(DateTime, nullable=True)
    
    # External identifiers
    external_id = Column(String(500), nullable=True)  # Cloud provider's stack ID
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, nullable=True)
    last_deployed = Column(DateTime, nullable=True)


class ResourceInventory(Base):
    """Cloud resource inventory model"""
    __tablename__ = "resource_inventory"

    id = Column(String(36), primary_key=True)
    stack_id = Column(String(36), nullable=False, index=True)
    stack_name = Column(String(255), nullable=False)
    
    # Resource details
    name = Column(String(500), nullable=False)
    resource_type = Column(String(100), nullable=False, index=True)
    resource_id = Column(String(500), nullable=True)  # Cloud provider's resource ID
    
    # Location
    cloud_provider = Column(String(50), nullable=False, index=True)
    region = Column(String(100), nullable=False)
    environment = Column(String(50), nullable=False, index=True)
    
    # Status
    status = Column(String(50), nullable=False)
    
    # Properties
    properties = Column(JSON, default={})
    tags = Column(JSON, default={})
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, nullable=True)


class DriftDetection(Base):
    """Infrastructure drift detection results"""
    __tablename__ = "drift_detections"

    id = Column(String(36), primary_key=True)
    stack_id = Column(String(36), nullable=False, index=True)
    stack_name = Column(String(255), nullable=False)
    
    # Drift status
    has_drift = Column(Boolean, default=False, nullable=False)
    drift_count = Column(Integer, default=0)
    
    # Details
    drifted_resources = Column(JSON, default=[])  # List of drifted resource names
    changes = Column(JSON, default={})  # Detailed changes
    
    # Timestamps
    detected_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class StateFileVersion(Base):
    """State file version tracking (primarily for Terraform)"""
    __tablename__ = "state_file_versions"

    id = Column(String(36), primary_key=True)
    stack_id = Column(String(36), nullable=False, index=True)
    
    # Version info
    version = Column(Integer, nullable=False)
    serial = Column(Integer, nullable=True)
    
    # File details
    size_bytes = Column(Integer, nullable=False)
    checksum = Column(String(64), nullable=False)  # SHA256
    storage_path = Column(String(1000), nullable=False)
    
    # Metadata
    created_by = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class CostEstimate(Base):
    """Infrastructure cost estimation"""
    __tablename__ = "cost_estimates"

    id = Column(String(36), primary_key=True)
    stack_id = Column(String(36), nullable=False, index=True)
    
    # Cost estimates
    estimated_monthly_cost = Column(Float, default=0.0)
    estimated_hourly_cost = Column(Float, default=0.0)
    currency = Column(String(10), default="USD")
    
    # Breakdown by service/resource type
    breakdown = Column(JSON, default={})
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class DeploymentHistory(Base):
    """Infrastructure deployment history"""
    __tablename__ = "deployment_history"

    id = Column(String(36), primary_key=True)
    stack_id = Column(String(36), nullable=False, index=True)
    stack_name = Column(String(255), nullable=False)
    
    # Deployment details
    action = Column(String(50), nullable=False)  # deploy, update, destroy
    status = Column(String(50), nullable=False)  # success, failed, cancelled
    environment = Column(String(50), nullable=False, index=True)
    
    # Changes applied
    changes = Column(JSON, default={})  # Resources added/modified/deleted
    
    # Execution details
    deployed_by = Column(String(255), nullable=False)
    deployed_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    duration_seconds = Column(Integer, nullable=True)
    
    # Error details (if failed)
    error_message = Column(Text, nullable=True)

"""
Unit tests for Infrastructure Service
"""

import pytest
from httpx import AsyncClient
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import app
from database import get_db, Base
from models import InfrastructureStack, ResourceInventory, DriftDetection

# Test database
TEST_DATABASE_URL = "sqlite:///./test_infrastructure.db"

engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create test database
Base.metadata.create_all(bind=engine)


def override_get_db():
    """Override database dependency for testing"""
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture
def client():
    """Test client fixture"""
    return TestClient(app)


@pytest.fixture
def db():
    """Database session fixture"""
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


# ============================================================================
# Health Check Tests
# ============================================================================

def test_health_endpoint(client):
    """Test health check endpoint"""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "infrastructure-service"
    assert "version" in data
    assert "timestamp" in data


def test_readiness_endpoint(client):
    """Test readiness check endpoint"""
    response = client.get("/ready")
    assert response.status_code == 200
    data = response.json()
    assert data["ready"] is True


# ============================================================================
# Stack Management Tests
# ============================================================================

def test_create_stack(client, db):
    """Test creating a new infrastructure stack"""
    stack_data = {
        "name": "test-stack",
        "provider": "terraform",
        "cloud_provider": "aws",
        "environment": "dev",
        "region": "us-east-1",
        "description": "Test stack",
        "repository_url": "https://github.com/example/repo",
        "branch": "main",
        "path": "/terraform",
        "variables": {"instance_type": "t3.medium"},
        "tags": {"team": "platform"}
    }
    
    response = client.post("/api/stacks", json=stack_data)
    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert data["name"] == "test-stack"
    assert data["status"] == "creating"


def test_list_stacks(client, db):
    """Test listing all stacks"""
    response = client.get("/api/stacks")
    assert response.status_code == 200
    data = response.json()
    assert "stacks" in data
    assert "total" in data
    assert isinstance(data["stacks"], list)


def test_get_stack(client, db):
    """Test getting stack details"""
    # Create a test stack first
    stack = InfrastructureStack(
        id="test-stack-id",
        name="test-stack",
        provider="terraform",
        cloud_provider="aws",
        environment="dev",
        region="us-east-1",
        status="active"
    )
    db.add(stack)
    db.commit()
    
    response = client.get(f"/api/stacks/{stack.id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == "test-stack-id"
    assert data["name"] == "test-stack"


def test_get_nonexistent_stack(client):
    """Test getting a non-existent stack"""
    response = client.get("/api/stacks/nonexistent-id")
    assert response.status_code == 404


# ============================================================================
# Resource Inventory Tests
# ============================================================================

def test_list_resources(client):
    """Test listing resources"""
    response = client.get("/api/resources")
    assert response.status_code == 200
    data = response.json()
    assert "resources" in data
    assert "total" in data


def test_get_resource_stats(client):
    """Test getting resource statistics"""
    response = client.get("/api/resources/stats")
    assert response.status_code == 200
    data = response.json()
    assert "total_resources" in data
    assert "by_cloud_provider" in data
    assert "by_type" in data
    assert "by_environment" in data


# ============================================================================
# Drift Detection Tests
# ============================================================================

def test_check_drift(client, db):
    """Test drift detection"""
    # Create a test stack
    stack = InfrastructureStack(
        id="test-drift-stack",
        name="drift-test",
        provider="terraform",
        cloud_provider="aws",
        environment="dev",
        region="us-east-1",
        status="active"
    )
    db.add(stack)
    db.commit()
    
    drift_request = {
        "stack_ids": ["test-drift-stack"]
    }
    
    response = client.post("/api/drift/check", json=drift_request)
    assert response.status_code == 200
    data = response.json()
    assert "message" in data
    assert "stack_ids" in data


def test_list_drift_detections(client):
    """Test listing drift detections"""
    response = client.get("/api/drift")
    assert response.status_code == 200
    data = response.json()
    assert "drift_detections" in data
    assert "total" in data


# ============================================================================
# Cost Estimation Tests
# ============================================================================

def test_estimate_cost(client, db):
    """Test cost estimation"""
    # Create a test stack
    stack = InfrastructureStack(
        id="test-cost-stack",
        name="cost-test",
        provider="terraform",
        cloud_provider="aws",
        environment="dev",
        region="us-east-1",
        status="active"
    )
    db.add(stack)
    db.commit()
    
    cost_request = {
        "stack_id": "test-cost-stack",
        "changes": {}
    }
    
    response = client.post("/api/cost/estimate", json=cost_request)
    assert response.status_code == 200
    data = response.json()
    assert "estimated_monthly_cost" in data
    assert "estimated_hourly_cost" in data
    assert "breakdown" in data


# ============================================================================
# Deployment History Tests
# ============================================================================

def test_list_deployments(client):
    """Test listing deployment history"""
    response = client.get("/api/deployments")
    assert response.status_code == 200
    data = response.json()
    assert "deployments" in data
    assert "total" in data


# ============================================================================
# Cleanup
# ============================================================================

@pytest.fixture(scope="session", autouse=True)
def cleanup():
    """Cleanup test database after all tests"""
    yield
    # Clean up test database
    if os.path.exists("./test_infrastructure.db"):
        os.remove("./test_infrastructure.db")

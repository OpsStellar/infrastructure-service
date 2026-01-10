"""
Unit tests for IaC provider integrations
"""

import pytest
from integrations import (
    TerraformAdapter,
    CloudFormationAdapter,
    AzureARMAdapter,
    GCPDeploymentAdapter
)


class MockStack:
    """Mock stack for testing"""
    def __init__(self):
        self.id = "test-stack-id"
        self.name = "test-stack"
        self.provider = "terraform"
        self.cloud_provider = "aws"
        self.environment = "dev"
        self.region = "us-east-1"


@pytest.mark.asyncio
async def test_terraform_deploy():
    """Test Terraform deployment"""
    adapter = TerraformAdapter()
    stack = MockStack()
    
    result = await adapter.deploy(stack)
    
    assert result["status"] == "success"
    assert result["provider"] == "terraform"
    assert "changes" in result


@pytest.mark.asyncio
async def test_terraform_drift_detection():
    """Test Terraform drift detection"""
    adapter = TerraformAdapter()
    stack = MockStack()
    
    result = await adapter.detect_drift(stack)
    
    assert "has_drift" in result
    assert "drift_count" in result
    assert "drifted_resources" in result


@pytest.mark.asyncio
async def test_cloudformation_deploy():
    """Test CloudFormation deployment"""
    adapter = CloudFormationAdapter()
    stack = MockStack()
    stack.provider = "cloudformation"
    
    result = await adapter.deploy(stack)
    
    assert result["status"] == "success"
    assert result["provider"] == "cloudformation"


@pytest.mark.asyncio
async def test_azure_arm_deploy():
    """Test Azure ARM deployment"""
    adapter = AzureARMAdapter()
    stack = MockStack()
    stack.provider = "arm"
    stack.cloud_provider = "azure"
    
    result = await adapter.deploy(stack)
    
    assert result["status"] == "success"
    assert result["provider"] == "arm"


@pytest.mark.asyncio
async def test_gcp_deployment_deploy():
    """Test GCP Deployment Manager deployment"""
    adapter = GCPDeploymentAdapter()
    stack = MockStack()
    stack.provider = "gcp_deployment"
    stack.cloud_provider = "gcp"
    
    result = await adapter.deploy(stack)
    
    assert result["status"] == "success"
    assert result["provider"] == "gcp_deployment"


@pytest.mark.asyncio
async def test_cost_estimation():
    """Test cost estimation across providers"""
    adapters = [
        TerraformAdapter(),
        CloudFormationAdapter(),
        AzureARMAdapter(),
        GCPDeploymentAdapter()
    ]
    
    stack = MockStack()
    
    for adapter in adapters:
        result = await adapter.estimate_cost(stack)
        
        assert "monthly_cost" in result
        assert "hourly_cost" in result
        assert "breakdown" in result
        assert result["monthly_cost"] > 0

"""
Infrastructure & Cloud Management Service
Unified infrastructure management across all IaC tools (Terraform, CloudFormation, ARM, GCP)
"""

from fastapi import FastAPI, HTTPException, Depends, WebSocket, WebSocketDisconnect, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_
from decimal import Decimal
import asyncio
import logging
import json
import uuid

from database import get_db
from models import (
    InfrastructureStack as DBStack,
    ResourceInventory as DBResource,
    DriftDetection as DBDrift,
    StateFileVersion as DBStateFile,
    CostEstimate as DBCostEstimate,
    DeploymentHistory as DBDeploymentHistory
)
from config import settings
from redis_cache import cache, cached
from websocket_manager import ws_manager
from otel_instrumentation import setup_instrumentation, shutdown_instrumentation
from integrations import (
    TerraformAdapter,
    CloudFormationAdapter,
    AzureARMAdapter,
    GCPDeploymentAdapter,
    IaCProvider
)

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL, logging.INFO),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# ============================================================================
# Pydantic Models
# ============================================================================

from pydantic import BaseModel, Field
from enum import Enum

class IaCProviderType(str, Enum):
    TERRAFORM = "terraform"
    CLOUDFORMATION = "cloudformation"
    ARM = "arm"
    GCP_DEPLOYMENT = "gcp_deployment"

class StackStatus(str, Enum):
    ACTIVE = "active"
    CREATING = "creating"
    UPDATING = "updating"
    DELETING = "deleting"
    FAILED = "failed"
    DRIFT_DETECTED = "drift_detected"

class DriftStatus(str, Enum):
    NO_DRIFT = "no_drift"
    DRIFT_DETECTED = "drift_detected"
    CHECKING = "checking"
    ERROR = "error"

class ResourceStatus(str, Enum):
    ACTIVE = "active"
    CREATING = "creating"
    UPDATING = "updating"
    DELETING = "deleting"
    DELETED = "deleted"
    FAILED = "failed"


class StackCreate(BaseModel):
    name: str
    provider: IaCProviderType
    cloud_provider: str  # aws, azure, gcp
    environment: str
    region: str
    description: Optional[str] = None
    repository_url: Optional[str] = None
    branch: str = "main"
    path: str = "/"
    variables: Optional[Dict[str, Any]] = None
    tags: Optional[Dict[str, str]] = None


class StackUpdate(BaseModel):
    description: Optional[str] = None
    status: Optional[StackStatus] = None
    variables: Optional[Dict[str, Any]] = None
    tags: Optional[Dict[str, str]] = None


class StackImport(BaseModel):
    provider: IaCProviderType
    cloud_provider: str
    stack_identifier: str  # Stack name, ID, or ARN
    environment: str
    region: str


class DriftCheckRequest(BaseModel):
    stack_ids: List[str]


class CostEstimationRequest(BaseModel):
    stack_id: str
    changes: Optional[Dict[str, Any]] = None


# ============================================================================
# Application Lifecycle
# ============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown lifecycle"""
    # Startup
    logger.info("🏗️ Infrastructure Management Service Starting...")
    
    # Setup OpenTelemetry instrumentation
    setup_instrumentation(app)
    
    # Start background tasks
    asyncio.create_task(periodic_drift_detection())
    asyncio.create_task(sync_resource_inventory())
    
    logger.info("✅ Infrastructure Service Ready")
    
    yield
    
    # Shutdown
    logger.info("⏹️ Infrastructure Service Shutting Down...")
    shutdown_instrumentation()
    await ws_manager.disconnect_all()


app = FastAPI(
    title="Infrastructure & Cloud Management Service",
    version="1.0.0",
    description="Unified infrastructure management across all IaC tools",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================================
# Health & Status Endpoints
# ============================================================================

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "infrastructure-service",
        "version": "1.0.0",
        "timestamp": datetime.utcnow().isoformat()
    }


@app.get("/ready")
async def readiness_check(db: Session = Depends(get_db)):
    """Readiness check for Kubernetes"""
    try:
        # Check database connectivity
        db.execute("SELECT 1")
        return {"ready": True, "checks": {"database": "healthy", "cache": "healthy"}}
    except Exception as e:
        logger.error(f"Readiness check failed: {e}")
        raise HTTPException(status_code=503, detail="Service not ready")


# ============================================================================
# Infrastructure Stack Management
# ============================================================================

@app.post("/api/stacks", status_code=201)
async def create_stack(
    stack: StackCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Create a new infrastructure stack"""
    
    # Create stack record
    db_stack = DBStack(
        id=str(uuid.uuid4()),
        name=stack.name,
        provider=stack.provider.value,
        cloud_provider=stack.cloud_provider,
        environment=stack.environment,
        region=stack.region,
        description=stack.description,
        repository_url=stack.repository_url,
        branch=stack.branch,
        path=stack.path,
        status=StackStatus.CREATING.value,
        variables=stack.variables or {},
        tags=stack.tags or {},
        created_at=datetime.utcnow()
    )
    
    db.add(db_stack)
    db.commit()
    db.refresh(db_stack)
    
    # Trigger async deployment
    background_tasks.add_task(deploy_stack, db_stack.id)
    
    # Broadcast event
    await ws_manager.broadcast({
        "type": "stack_created",
        "stack_id": db_stack.id,
        "name": db_stack.name,
        "timestamp": datetime.utcnow().isoformat()
    })
    
    logger.info(f"Created stack {db_stack.name} ({db_stack.id})")
    
    return {
        "id": db_stack.id,
        "name": db_stack.name,
        "status": db_stack.status,
        "message": "Stack creation initiated"
    }


@app.get("/api/stacks")
@cached(ttl=60)
async def list_stacks(
    environment: Optional[str] = None,
    provider: Optional[IaCProviderType] = None,
    cloud_provider: Optional[str] = None,
    status: Optional[StackStatus] = None,
    db: Session = Depends(get_db)
):
    """List all infrastructure stacks with filters"""
    
    query = db.query(DBStack)
    
    if environment:
        query = query.filter(DBStack.environment == environment)
    if provider:
        query = query.filter(DBStack.provider == provider.value)
    if cloud_provider:
        query = query.filter(DBStack.cloud_provider == cloud_provider)
    if status:
        query = query.filter(DBStack.status == status.value)
    
    stacks = query.order_by(DBStack.created_at.desc()).all()
    
    return {
        "stacks": [
            {
                "id": s.id,
                "name": s.name,
                "provider": s.provider,
                "cloud_provider": s.cloud_provider,
                "environment": s.environment,
                "region": s.region,
                "status": s.status,
                "resource_count": s.resource_count,
                "last_drift_check": s.last_drift_check.isoformat() if s.last_drift_check else None,
                "drift_status": s.drift_status,
                "created_at": s.created_at.isoformat(),
                "updated_at": s.updated_at.isoformat() if s.updated_at else None
            }
            for s in stacks
        ],
        "total": len(stacks)
    }


@app.get("/api/stacks/{stack_id}")
@cached(ttl=30)
async def get_stack(stack_id: str, db: Session = Depends(get_db)):
    """Get detailed stack information"""
    
    stack = db.query(DBStack).filter(DBStack.id == stack_id).first()
    if not stack:
        raise HTTPException(status_code=404, detail="Stack not found")
    
    # Get resources count by type
    resources = db.query(
        DBResource.resource_type,
        func.count(DBResource.id).label('count')
    ).filter(
        DBResource.stack_id == stack_id
    ).group_by(DBResource.resource_type).all()
    
    return {
        "id": stack.id,
        "name": stack.name,
        "provider": stack.provider,
        "cloud_provider": stack.cloud_provider,
        "environment": stack.environment,
        "region": stack.region,
        "status": stack.status,
        "description": stack.description,
        "repository_url": stack.repository_url,
        "branch": stack.branch,
        "path": stack.path,
        "variables": stack.variables,
        "tags": stack.tags,
        "resource_count": stack.resource_count,
        "resources_by_type": {r.resource_type: r.count for r in resources},
        "drift_status": stack.drift_status,
        "last_drift_check": stack.last_drift_check.isoformat() if stack.last_drift_check else None,
        "last_deployed": stack.last_deployed.isoformat() if stack.last_deployed else None,
        "created_at": stack.created_at.isoformat(),
        "updated_at": stack.updated_at.isoformat() if stack.updated_at else None
    }


@app.put("/api/stacks/{stack_id}")
async def update_stack(
    stack_id: str,
    stack_update: StackUpdate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Update stack configuration"""
    
    stack = db.query(DBStack).filter(DBStack.id == stack_id).first()
    if not stack:
        raise HTTPException(status_code=404, detail="Stack not found")
    
    # Update fields
    if stack_update.description is not None:
        stack.description = stack_update.description
    if stack_update.variables is not None:
        stack.variables = stack_update.variables
    if stack_update.tags is not None:
        stack.tags = stack_update.tags
    
    stack.updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(stack)
    
    # Trigger re-deployment if variables changed
    if stack_update.variables is not None:
        background_tasks.add_task(deploy_stack, stack_id)
    
    cache.invalidate(f"stack:{stack_id}")
    
    return {"message": "Stack updated successfully", "stack_id": stack_id}


@app.delete("/api/stacks/{stack_id}")
async def delete_stack(
    stack_id: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Delete infrastructure stack"""
    
    stack = db.query(DBStack).filter(DBStack.id == stack_id).first()
    if not stack:
        raise HTTPException(status_code=404, detail="Stack not found")
    
    # Update status
    stack.status = StackStatus.DELETING.value
    stack.updated_at = datetime.utcnow()
    db.commit()
    
    # Trigger async deletion
    background_tasks.add_task(destroy_stack, stack_id)
    
    return {"message": "Stack deletion initiated", "stack_id": stack_id}


@app.post("/api/stacks/import")
async def import_stack(
    import_request: StackImport,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Import existing infrastructure stack"""
    
    logger.info(f"Importing stack: {import_request.stack_identifier}")
    
    # Create adapter based on provider
    adapter = get_adapter(import_request.provider)
    
    # Fetch stack details from cloud provider
    try:
        stack_details = await adapter.get_stack_details(import_request.stack_identifier)
    except Exception as e:
        logger.error(f"Failed to import stack: {e}")
        raise HTTPException(status_code=400, detail=f"Failed to import stack: {str(e)}")
    
    # Create stack record
    db_stack = DBStack(
        id=str(uuid.uuid4()),
        name=stack_details.get("name", import_request.stack_identifier),
        provider=import_request.provider.value,
        cloud_provider=import_request.cloud_provider,
        environment=import_request.environment,
        region=import_request.region,
        status=StackStatus.ACTIVE.value,
        resource_count=stack_details.get("resource_count", 0),
        external_id=import_request.stack_identifier,
        tags=stack_details.get("tags", {}),
        created_at=datetime.utcnow()
    )
    
    db.add(db_stack)
    db.commit()
    db.refresh(db_stack)
    
    # Trigger resource inventory sync
    background_tasks.add_task(sync_stack_resources, db_stack.id)
    
    logger.info(f"Imported stack {db_stack.name} ({db_stack.id})")
    
    return {
        "id": db_stack.id,
        "name": db_stack.name,
        "message": "Stack imported successfully"
    }


# ============================================================================
# Resource Inventory
# ============================================================================

@app.get("/api/resources")
@cached(ttl=120)
async def list_resources(
    stack_id: Optional[str] = None,
    resource_type: Optional[str] = None,
    cloud_provider: Optional[str] = None,
    environment: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """List all infrastructure resources"""
    
    query = db.query(DBResource)
    
    if stack_id:
        query = query.filter(DBResource.stack_id == stack_id)
    if resource_type:
        query = query.filter(DBResource.resource_type == resource_type)
    if cloud_provider:
        query = query.filter(DBResource.cloud_provider == cloud_provider)
    if environment:
        query = query.filter(DBResource.environment == environment)
    
    resources = query.order_by(DBResource.created_at.desc()).limit(500).all()
    
    return {
        "resources": [
            {
                "id": r.id,
                "name": r.name,
                "resource_type": r.resource_type,
                "cloud_provider": r.cloud_provider,
                "region": r.region,
                "environment": r.environment,
                "status": r.status,
                "stack_id": r.stack_id,
                "stack_name": r.stack_name,
                "properties": r.properties,
                "tags": r.tags,
                "created_at": r.created_at.isoformat()
            }
            for r in resources
        ],
        "total": len(resources)
    }


@app.get("/api/resources/stats")
@cached(ttl=300)
async def get_resource_stats(db: Session = Depends(get_db)):
    """Get resource statistics across all providers"""
    
    # Resources by cloud provider
    by_provider = db.query(
        DBResource.cloud_provider,
        func.count(DBResource.id).label('count')
    ).group_by(DBResource.cloud_provider).all()
    
    # Resources by type
    by_type = db.query(
        DBResource.resource_type,
        func.count(DBResource.id).label('count')
    ).group_by(DBResource.resource_type).order_by(func.count(DBResource.id).desc()).limit(10).all()
    
    # Resources by environment
    by_environment = db.query(
        DBResource.environment,
        func.count(DBResource.id).label('count')
    ).group_by(DBResource.environment).all()
    
    # Total count
    total = db.query(func.count(DBResource.id)).scalar()
    
    return {
        "total_resources": total,
        "by_cloud_provider": [{"provider": p.cloud_provider, "count": p.count} for p in by_provider],
        "by_type": [{"type": t.resource_type, "count": t.count} for t in by_type],
        "by_environment": [{"environment": e.environment, "count": e.count} for e in by_environment]
    }


# ============================================================================
# Drift Detection
# ============================================================================

@app.post("/api/drift/check")
async def check_drift(
    drift_request: DriftCheckRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Trigger drift detection for specified stacks"""
    
    for stack_id in drift_request.stack_ids:
        stack = db.query(DBStack).filter(DBStack.id == stack_id).first()
        if stack:
            stack.drift_status = DriftStatus.CHECKING.value
            stack.last_drift_check = datetime.utcnow()
            
            background_tasks.add_task(detect_stack_drift, stack_id)
    
    db.commit()
    
    return {
        "message": f"Drift detection initiated for {len(drift_request.stack_ids)} stacks",
        "stack_ids": drift_request.stack_ids
    }


@app.get("/api/drift")
@cached(ttl=60)
async def list_drift_detections(
    stack_id: Optional[str] = None,
    has_drift: Optional[bool] = None,
    days: int = 7,
    db: Session = Depends(get_db)
):
    """List drift detection results"""
    
    start_date = datetime.utcnow() - timedelta(days=days)
    query = db.query(DBDrift).filter(DBDrift.detected_at >= start_date)
    
    if stack_id:
        query = query.filter(DBDrift.stack_id == stack_id)
    if has_drift is not None:
        query = query.filter(DBDrift.has_drift == has_drift)
    
    drifts = query.order_by(DBDrift.detected_at.desc()).all()
    
    return {
        "drift_detections": [
            {
                "id": d.id,
                "stack_id": d.stack_id,
                "stack_name": d.stack_name,
                "has_drift": d.has_drift,
                "drift_count": d.drift_count,
                "drifted_resources": d.drifted_resources,
                "changes": d.changes,
                "detected_at": d.detected_at.isoformat()
            }
            for d in drifts
        ],
        "total": len(drifts)
    }


# ============================================================================
# Cost Estimation
# ============================================================================

@app.post("/api/cost/estimate")
async def estimate_cost(
    cost_request: CostEstimationRequest,
    db: Session = Depends(get_db)
):
    """Estimate infrastructure cost before deployment"""
    
    stack = db.query(DBStack).filter(DBStack.id == cost_request.stack_id).first()
    if not stack:
        raise HTTPException(status_code=404, detail="Stack not found")
    
    # Get adapter
    adapter = get_adapter(IaCProviderType(stack.provider))
    
    try:
        # Calculate cost estimation
        estimation = await adapter.estimate_cost(stack, cost_request.changes)
        
        # Save estimation
        db_estimate = DBCostEstimate(
            id=str(uuid.uuid4()),
            stack_id=stack.id,
            estimated_monthly_cost=estimation.get("monthly_cost", 0),
            estimated_hourly_cost=estimation.get("hourly_cost", 0),
            breakdown=estimation.get("breakdown", {}),
            created_at=datetime.utcnow()
        )
        
        db.add(db_estimate)
        db.commit()
        
        return {
            "stack_id": stack.id,
            "stack_name": stack.name,
            "estimated_monthly_cost": estimation.get("monthly_cost", 0),
            "estimated_hourly_cost": estimation.get("hourly_cost", 0),
            "currency": "USD",
            "breakdown": estimation.get("breakdown", {}),
            "estimated_at": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Cost estimation failed: {e}")
        raise HTTPException(status_code=500, detail=f"Cost estimation failed: {str(e)}")


# ============================================================================
# Deployment History
# ============================================================================

@app.get("/api/deployments")
@cached(ttl=60)
async def list_deployments(
    stack_id: Optional[str] = None,
    environment: Optional[str] = None,
    days: int = 30,
    db: Session = Depends(get_db)
):
    """List infrastructure deployment history"""
    
    start_date = datetime.utcnow() - timedelta(days=days)
    query = db.query(DBDeploymentHistory).filter(DBDeploymentHistory.deployed_at >= start_date)
    
    if stack_id:
        query = query.filter(DBDeploymentHistory.stack_id == stack_id)
    if environment:
        query = query.filter(DBDeploymentHistory.environment == environment)
    
    deployments = query.order_by(DBDeploymentHistory.deployed_at.desc()).limit(100).all()
    
    return {
        "deployments": [
            {
                "id": d.id,
                "stack_id": d.stack_id,
                "stack_name": d.stack_name,
                "action": d.action,
                "status": d.status,
                "environment": d.environment,
                "changes": d.changes,
                "deployed_by": d.deployed_by,
                "deployed_at": d.deployed_at.isoformat(),
                "duration_seconds": d.duration_seconds
            }
            for d in deployments
        ],
        "total": len(deployments)
    }


# ============================================================================
# State File Management
# ============================================================================

@app.get("/api/stacks/{stack_id}/state")
async def get_state_versions(stack_id: str, db: Session = Depends(get_db)):
    """Get state file versions for a stack"""
    
    versions = db.query(DBStateFile).filter(
        DBStateFile.stack_id == stack_id
    ).order_by(DBStateFile.created_at.desc()).limit(20).all()
    
    return {
        "stack_id": stack_id,
        "versions": [
            {
                "id": v.id,
                "version": v.version,
                "size_bytes": v.size_bytes,
                "checksum": v.checksum,
                "created_by": v.created_by,
                "created_at": v.created_at.isoformat()
            }
            for v in versions
        ]
    }


# ============================================================================
# WebSocket Endpoint for Real-time Updates
# ============================================================================

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket connection for real-time infrastructure updates"""
    await ws_manager.connect(websocket)
    try:
        while True:
            # Keep connection alive and handle incoming messages
            data = await websocket.receive_text()
            # Echo back for connection testing
            await websocket.send_json({"type": "pong", "timestamp": datetime.utcnow().isoformat()})
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)
        logger.info("WebSocket client disconnected")


# ============================================================================
# Background Tasks
# ============================================================================

async def deploy_stack(stack_id: str):
    """Background task to deploy infrastructure stack"""
    logger.info(f"Deploying stack {stack_id}")
    
    db = next(get_db())
    stack = db.query(DBStack).filter(DBStack.id == stack_id).first()
    
    if not stack:
        return
    
    try:
        adapter = get_adapter(IaCProviderType(stack.provider))
        result = await adapter.deploy(stack)
        
        # Update stack status
        stack.status = StackStatus.ACTIVE.value
        stack.last_deployed = datetime.utcnow()
        stack.updated_at = datetime.utcnow()
        
        # Create deployment history
        deployment = DBDeploymentHistory(
            id=str(uuid.uuid4()),
            stack_id=stack.id,
            stack_name=stack.name,
            action="deploy",
            status="success",
            environment=stack.environment,
            changes=result.get("changes", {}),
            deployed_by="system",
            deployed_at=datetime.utcnow(),
            duration_seconds=result.get("duration", 0)
        )
        db.add(deployment)
        db.commit()
        
        # Broadcast success
        await ws_manager.broadcast({
            "type": "deployment_success",
            "stack_id": stack_id,
            "stack_name": stack.name,
            "timestamp": datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Stack deployment failed: {e}")
        stack.status = StackStatus.FAILED.value
        stack.updated_at = datetime.utcnow()
        db.commit()
        
        await ws_manager.broadcast({
            "type": "deployment_failed",
            "stack_id": stack_id,
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        })


async def destroy_stack(stack_id: str):
    """Background task to destroy infrastructure stack"""
    logger.info(f"Destroying stack {stack_id}")
    
    db = next(get_db())
    stack = db.query(DBStack).filter(DBStack.id == stack_id).first()
    
    if not stack:
        return
    
    try:
        adapter = get_adapter(IaCProviderType(stack.provider))
        await adapter.destroy(stack)
        
        # Delete stack record
        db.delete(stack)
        db.commit()
        
        logger.info(f"Stack {stack_id} destroyed successfully")
        
    except Exception as e:
        logger.error(f"Stack destruction failed: {e}")
        stack.status = StackStatus.FAILED.value
        db.commit()


async def detect_stack_drift(stack_id: str):
    """Background task to detect infrastructure drift"""
    logger.info(f"Detecting drift for stack {stack_id}")
    
    db = next(get_db())
    stack = db.query(DBStack).filter(DBStack.id == stack_id).first()
    
    if not stack:
        return
    
    try:
        adapter = get_adapter(IaCProviderType(stack.provider))
        drift_result = await adapter.detect_drift(stack)
        
        # Update stack drift status
        has_drift = drift_result.get("has_drift", False)
        stack.drift_status = DriftStatus.DRIFT_DETECTED.value if has_drift else DriftStatus.NO_DRIFT.value
        stack.last_drift_check = datetime.utcnow()
        
        # Save drift detection record
        drift = DBDrift(
            id=str(uuid.uuid4()),
            stack_id=stack.id,
            stack_name=stack.name,
            has_drift=has_drift,
            drift_count=drift_result.get("drift_count", 0),
            drifted_resources=drift_result.get("drifted_resources", []),
            changes=drift_result.get("changes", {}),
            detected_at=datetime.utcnow()
        )
        db.add(drift)
        db.commit()
        
        # Broadcast drift alert if detected
        if has_drift:
            await ws_manager.broadcast({
                "type": "drift_detected",
                "stack_id": stack_id,
                "stack_name": stack.name,
                "drift_count": drift_result.get("drift_count", 0),
                "timestamp": datetime.utcnow().isoformat()
            })
        
    except Exception as e:
        logger.error(f"Drift detection failed: {e}")
        stack.drift_status = DriftStatus.ERROR.value
        db.commit()


async def sync_stack_resources(stack_id: str):
    """Sync resource inventory for a stack"""
    logger.info(f"Syncing resources for stack {stack_id}")
    
    db = next(get_db())
    stack = db.query(DBStack).filter(DBStack.id == stack_id).first()
    
    if not stack:
        return
    
    try:
        adapter = get_adapter(IaCProviderType(stack.provider))
        resources = await adapter.list_resources(stack)
        
        # Update resource inventory
        for resource_data in resources:
            resource = DBResource(
                id=str(uuid.uuid4()),
                stack_id=stack.id,
                stack_name=stack.name,
                name=resource_data["name"],
                resource_type=resource_data["type"],
                cloud_provider=stack.cloud_provider,
                region=stack.region,
                environment=stack.environment,
                status=resource_data.get("status", "active"),
                properties=resource_data.get("properties", {}),
                tags=resource_data.get("tags", {}),
                created_at=datetime.utcnow()
            )
            db.add(resource)
        
        # Update resource count
        stack.resource_count = len(resources)
        db.commit()
        
    except Exception as e:
        logger.error(f"Resource sync failed: {e}")


async def periodic_drift_detection():
    """Periodic drift detection for all active stacks"""
    while True:
        await asyncio.sleep(3600)  # Run every hour
        
        logger.info("Running periodic drift detection")
        
        db = next(get_db())
        stacks = db.query(DBStack).filter(
            DBStack.status == StackStatus.ACTIVE.value
        ).all()
        
        for stack in stacks:
            await detect_stack_drift(stack.id)


async def sync_resource_inventory():
    """Periodic resource inventory synchronization"""
    while True:
        await asyncio.sleep(1800)  # Run every 30 minutes
        
        logger.info("Running resource inventory sync")
        
        db = next(get_db())
        stacks = db.query(DBStack).filter(
            DBStack.status == StackStatus.ACTIVE.value
        ).all()
        
        for stack in stacks:
            await sync_stack_resources(stack.id)


# ============================================================================
# Helper Functions
# ============================================================================

def get_adapter(provider: IaCProviderType):
    """Get the appropriate IaC adapter based on provider type"""
    if provider == IaCProviderType.TERRAFORM:
        return TerraformAdapter()
    elif provider == IaCProviderType.CLOUDFORMATION:
        return CloudFormationAdapter()
    elif provider == IaCProviderType.ARM:
        return AzureARMAdapter()
    elif provider == IaCProviderType.GCP_DEPLOYMENT:
        return GCPDeploymentAdapter()
    else:
        raise ValueError(f"Unsupported provider: {provider}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8030)

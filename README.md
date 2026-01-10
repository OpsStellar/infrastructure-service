# Infrastructure & Cloud Management Service 🏗️

> Unified infrastructure management across all IaC tools - Terraform, CloudFormation, Azure ARM, and GCP Deployment Manager

Part of the **Opsstellar DevOps Control Plane** platform.

## 📋 Overview

The Infrastructure Service provides comprehensive infrastructure as code (IaC) management capabilities, enabling teams to:

- **Manage Multi-Cloud Infrastructure** across AWS, Azure, and GCP
- **Track Infrastructure Drift** with automated detection
- **Estimate Costs** before deployment
- **Visualize Resources** across all cloud providers
- **Monitor Deployments** with detailed history tracking
- **Version State Files** for Terraform

## ✨ Features

### 🎯 Core Features

- **Multi-IaC Provider Support**

  - Terraform
  - AWS CloudFormation
  - Azure ARM Templates
  - GCP Deployment Manager

- **Stack Management**

  - Create, update, and delete infrastructure stacks
  - Import existing stacks from cloud providers
  - Track stack status and deployment history

- **Drift Detection**

  - Automated drift detection across all stacks
  - Real-time drift alerts via WebSocket
  - Detailed change tracking

- **Resource Inventory**

  - Multi-cloud resource inventory
  - Resource categorization by type, provider, environment
  - Resource lifecycle tracking

- **Cost Estimation**

  - Pre-deployment cost estimation
  - Cost breakdown by resource type
  - Monthly and hourly cost projections

- **State Management** (Terraform)
  - State file versioning
  - State file storage and retrieval
  - State locking support

### 🔄 Real-time Updates

- WebSocket support for live updates
- Deployment progress streaming
- Drift alert notifications
- Resource inventory changes

### 📊 Observability

- Full OpenTelemetry instrumentation
- Request/response tracing
- Database query monitoring
- External API call tracking

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- PostgreSQL 13+ (production) or SQLite (development)
- Redis 6+
- Docker & Docker Compose (optional)

### Installation

1. **Clone the repository**

```bash
git clone https://github.com/opsstellar/infrastructure-service.git
cd infrastructure-service
```

2. **Create virtual environment**

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies**

```bash
pip install -r requirements.txt
```

4. **Configure environment variables**

```bash
cp .env.example .env
# Edit .env with your configuration
```

5. **Run the service**

```bash
uvicorn main:app --host 0.0.0.0 --port 8030 --reload
```

### Docker Deployment

```bash
# Start all services
docker compose up -d

# View logs
docker compose logs -f infrastructure-service

# Stop services
docker compose down
```

## 📡 API Endpoints

### Health & Status

- `GET /health` - Health check
- `GET /ready` - Readiness check for Kubernetes

### Stack Management

- `POST /api/stacks` - Create new infrastructure stack
- `GET /api/stacks` - List all stacks
- `GET /api/stacks/{stack_id}` - Get stack details
- `PUT /api/stacks/{stack_id}` - Update stack
- `DELETE /api/stacks/{stack_id}` - Delete stack
- `POST /api/stacks/import` - Import existing stack

### Resource Inventory

- `GET /api/resources` - List all resources
- `GET /api/resources/stats` - Get resource statistics

### Drift Detection

- `POST /api/drift/check` - Trigger drift detection
- `GET /api/drift` - List drift detection results

### Cost Estimation

- `POST /api/cost/estimate` - Estimate infrastructure cost

### Deployment History

- `GET /api/deployments` - List deployment history

### State Management

- `GET /api/stacks/{stack_id}/state` - Get state file versions

### WebSocket

- `WS /ws` - Real-time infrastructure updates

## 🔧 Configuration

### Environment Variables

```bash
# Service Configuration
DEBUG=false
LOG_LEVEL=INFO

# Database
DATABASE_URL=postgresql://user:pass@localhost:5432/infrastructure_db

# Redis Cache
REDIS_URL=redis://localhost:6379/0
CACHE_TTL=300

# Service URLs
AUTH_SERVICE_URL=http://auth-service:8001
SETTINGS_SERVICE_URL=http://settings-service:8020
COST_SERVICE_URL=http://cost-service:8010

# OpenTelemetry
OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317

# IaC Provider Configuration
ENABLE_TERRAFORM=true
ENABLE_CLOUDFORMATION=true
ENABLE_ARM=true
ENABLE_GCP_DEPLOYMENT=true

# Cloud Provider Credentials (optional - can be fetched from settings-service)
AWS_REGION=us-east-1
AZURE_SUBSCRIPTION_ID=xxx
GCP_PROJECT_ID=xxx

# Background Tasks
DRIFT_CHECK_INTERVAL_HOURS=24
RESOURCE_SYNC_INTERVAL_MINUTES=30
```

### Cloud Provider Setup

#### AWS (CloudFormation & Terraform)

```bash
# Option 1: Environment variables
export AWS_ACCESS_KEY_ID=your_access_key
export AWS_SECRET_ACCESS_KEY=your_secret_key
export AWS_REGION=us-east-1

# Option 2: Store in settings-service (recommended)
# POST /api/integrations/aws/credentials
```

#### Azure (ARM Templates)

```bash
# Option 1: Environment variables
export AZURE_SUBSCRIPTION_ID=xxx
export AZURE_TENANT_ID=xxx
export AZURE_CLIENT_ID=xxx
export AZURE_CLIENT_SECRET=xxx

# Option 2: Store in settings-service (recommended)
```

#### GCP (Deployment Manager)

```bash
# Option 1: Service account key file
export GCP_PROJECT_ID=your-project-id
export GCP_SERVICE_ACCOUNT_KEY=/path/to/key.json

# Option 2: Store in settings-service (recommended)
```

## 🧪 Testing

### Run Unit Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=. --cov-report=html

# Run specific test file
pytest unit-test/test_main.py

# Run with markers
pytest -m unit
```

### Test Coverage

Current test coverage: **70%+**

Coverage reports are generated in `htmlcov/index.html`

## 📦 Kubernetes Deployment

### Using Helm

```bash
# Add Opsstellar Helm repository
helm repo add opsstellar https://charts.opsstellar.io
helm repo update

# Install
helm install infrastructure-service opsstellar/infrastructure-service \
  --namespace opsstellar \
  --create-namespace \
  --set database.existingSecret=infrastructure-db-secret

# Upgrade
helm upgrade infrastructure-service opsstellar/infrastructure-service \
  --namespace opsstellar

# Uninstall
helm uninstall infrastructure-service --namespace opsstellar
```

### Custom Values

```yaml
# custom-values.yaml
replicaCount: 3

resources:
  limits:
    cpu: 2000m
    memory: 2Gi
  requests:
    cpu: 1000m
    memory: 1Gi

autoscaling:
  enabled: true
  minReplicas: 3
  maxReplicas: 10

ingress:
  enabled: true
  hosts:
    - host: infrastructure.yourdomain.com
      paths:
        - path: /
          pathType: Prefix

env:
  ENABLE_TERRAFORM: "true"
  ENABLE_CLOUDFORMATION: "true"
  DRIFT_CHECK_INTERVAL_HOURS: "12"
```

Install with custom values:

```bash
helm install infrastructure-service opsstellar/infrastructure-service \
  -f custom-values.yaml
```

## 🔐 Security

### Authentication

This service integrates with **auth-service** for SSO authentication:

```python
from fastapi import Depends, Security
from fastapi.security import HTTPBearer

async def verify_token(credentials: HTTPAuthorizationCredentials = Security(HTTPBearer())):
    # Token validation with auth-service
    pass
```

### Secrets Management

- Never commit credentials to version control
- Use **settings-service** for centralized credential management
- Use Kubernetes secrets in production
- Rotate credentials regularly

### Best Practices

1. Use least-privilege IAM roles/service principals
2. Enable audit logging for all infrastructure changes
3. Implement approval workflows for production deployments
4. Regularly review drift detection results
5. Monitor cost estimates before deployments

## 🔄 Integration with Other Services

### Auth Service

- Single Sign-On (SSO) authentication
- Token validation
- User authorization

### Settings Service

- Centralized credential storage
- Cloud provider configurations
- Integration settings

### Cost Service

- Infrastructure cost tracking
- Cost optimization recommendations
- Budget alerts

## 📊 Monitoring & Observability

### OpenTelemetry

The service is fully instrumented with OpenTelemetry:

- **Traces**: Distributed tracing for all API calls
- **Metrics**: Request counts, latencies, error rates
- **Logs**: Structured logging with context

### Metrics Exported

- `http_requests_total` - Total HTTP requests
- `http_request_duration_seconds` - Request latency
- `infrastructure_stacks_total` - Total stacks by provider
- `infrastructure_drift_detected` - Drift detection count
- `infrastructure_deployments_total` - Deployment count

### Health Checks

```bash
# Health check
curl http://localhost:8030/health

# Readiness check
curl http://localhost:8030/ready
```

## 🐛 Troubleshooting

### Common Issues

**Issue: Service fails to start**

```bash
# Check database connectivity
pg_isready -h localhost -p 5432

# Check Redis connectivity
redis-cli ping

# View logs
docker compose logs infrastructure-service
```

**Issue: Drift detection not working**

```bash
# Verify cloud provider credentials
# Check settings-service for stored credentials
# Review logs for authentication errors
```

**Issue: Cost estimation failing**

```bash
# Ensure cloud provider APIs are accessible
# Verify API quotas and limits
# Check cost estimation provider configuration
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'feat: add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Coding Standards

- Follow [Opsstellar Coding Guidelines](../.copilot-instructions.md)
- Maintain 70%+ test coverage
- Use type hints for all functions
- Document all public APIs
- Use conventional commits

## 📝 License

Copyright © 2026 Opsstellar. All rights reserved.

## 🆘 Support

- Documentation: https://docs.opsstellar.io
- Issue Tracker: https://github.com/opsstellar/infrastructure-service/issues
- Slack: https://opsstellar.slack.com
- Email: support@opsstellar.io

## 🗺️ Roadmap

- [ ] Ansible playbook support
- [ ] Pulumi integration
- [ ] CDK (AWS/Terraform) support
- [ ] Cost optimization recommendations
- [ ] Infrastructure compliance scanning
- [ ] Multi-region failover support
- [ ] Infrastructure change approvals
- [ ] Automated rollback on drift detection
- [ ] Infrastructure policy enforcement (OPA)

---

**Built with ❤️ by the Opsstellar Team**

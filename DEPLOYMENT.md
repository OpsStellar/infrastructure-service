# Infrastructure Service - Deployment Guide

## 🚀 Quick Start

### 1. Start the Infrastructure Service

```bash
cd infrastructure-service

# Copy environment variables
cp .env.example .env

# Edit .env with your configuration
nano .env

# Start with Docker Compose
docker compose up -d

# View logs
docker compose logs -f infrastructure-service
```

### 2. Verify Service is Running

```bash
# Health check
curl http://localhost:8030/health

# Expected response:
# {"status":"healthy","service":"infrastructure-service","version":"1.0.0","timestamp":"2026-01-10T..."}

# Readiness check
curl http://localhost:8030/ready
```

### 3. Access the Frontend

1. Navigate to OpsStellar Dashboard: `http://localhost:3000`
2. Click on **"🏗️ Infrastructure as Code"** in the sidebar
3. Select **"Infrastructure Management"**

## 📡 API Endpoints Available

- **POST** `/api/stacks` - Create new stack
- **GET** `/api/stacks` - List all stacks
- **GET** `/api/stacks/{stack_id}` - Get stack details
- **GET** `/api/resources` - List resources
- **GET** `/api/resources/stats` - Get resource statistics
- **POST** `/api/drift/check` - Trigger drift detection
- **POST** `/api/cost/estimate` - Estimate infrastructure cost
- **GET** `/api/deployments` - List deployment history

## 🔧 Configuration

### Required Environment Variables

```bash
# Database
DATABASE_URL=postgresql://postgres:postgres@postgres:5432/infrastructure_db

# Redis
REDIS_URL=redis://redis:6379/0

# Service URLs
AUTH_SERVICE_URL=http://auth-service:8001
SETTINGS_SERVICE_URL=http://settings-service:8020
```

### Cloud Provider Setup

Store credentials in settings-service for security:

```bash
# Using settings-service API
curl -X POST http://localhost:8020/api/integrations/aws/credentials \
  -H "Content-Type: application/json" \
  -d '{
    "access_key_id": "YOUR_AWS_KEY",
    "secret_access_key": "YOUR_AWS_SECRET",
    "region": "us-east-1"
  }'
```

## 🐳 Docker Network Setup

Ensure the Opsstellar network exists:

```bash
# Create network if not exists
docker network create opsstellar-network

# Verify
docker network ls | grep opsstellar
```

## 🎯 Next Steps

1. **Import Existing Stacks**: Use the "Import Stack" feature
2. **Enable Drift Detection**: Stacks are automatically checked every 24 hours
3. **Set Up Cost Monitoring**: Integrate with cost-service
4. **Configure Alerts**: Set up drift alert notifications

## 📊 Monitoring

View OpenTelemetry traces at: `http://localhost:16686` (Jaeger UI)

## 🆘 Troubleshooting

**Service won't start:**

```bash
# Check logs
docker compose logs infrastructure-service

# Verify database connectivity
docker compose exec postgres pg_isready

# Verify Redis
docker compose exec redis redis-cli ping
```

**Can't see stacks in UI:**

- Verify frontend environment variable: `REACT_APP_INFRASTRUCTURE_SERVICE_URL=http://localhost:8030`
- Check browser console for errors
- Verify CORS settings in main.py

## ✅ Success Checklist

- [ ] Service health endpoint responds
- [ ] Frontend shows IaC menu item
- [ ] Can create/list stacks
- [ ] Resource inventory populates
- [ ] Drift detection works
- [ ] Cost estimation returns data

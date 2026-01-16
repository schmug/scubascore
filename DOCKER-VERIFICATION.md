# Docker Deployment End-to-End Verification

This document describes the comprehensive verification process for the ScubaScore Docker deployment.

## Overview

The Docker containerization implementation includes:
- **Dockerfile**: Production-ready Python 3.11 image with gunicorn WSGI server
- **docker-compose.yml**: Complete deployment configuration with persistent volumes
- **Health Check Endpoint**: `/health` endpoint for container orchestration
- **Environment Configuration**: Flexible configuration via environment variables
- **Data Persistence**: SQLite database and autoload directories with volume mounts

## Automated Verification

### Quick Start

```bash
# Make the script executable
chmod +x ./test-e2e.sh

# Run all verification tests
./test-e2e.sh
```

The script will automatically:
1. Clean up any existing containers and volumes
2. Start fresh containers with `docker-compose up -d`
3. Wait for health check to pass
4. Test API endpoints with sample data
5. Verify database file creation
6. Restart containers to test persistence
7. Verify data survived the restart
8. Check volume mounting and configuration
9. Display container logs
10. Clean up and provide summary

### Expected Output

```
==========================================
ScubaScore Docker E2E Verification
==========================================

✓ All prerequisites met
✓ Cleanup complete
✓ Containers started
✓ Health check passed (HTTP 200)
✓ Health endpoint returns correct response: {"status":"ok"}
✓ Score endpoint accepted data
✓ Database file exists: ./data/scubascore.db
✓ Score history retrieved: 1 record(s)
✓ Containers restarted
✓ Health check passed after restart
✓ Data persisted after restart: 1 record(s)
✓ Autoload directory exists: ./autoload
✓ Container health status: healthy
✓ Environment variables applied
✓ Database volume mounted correctly
✓ Autoload volume mounted correctly
✓ Config files mounted correctly
✓ Containers stopped

==========================================
✓ All E2E verification tests passed!
==========================================
```

## Manual Verification Steps

If you prefer to run verification manually, follow these steps:

### Prerequisites

Ensure you have installed:
- Docker (v20.10+)
- docker-compose (v1.29+ or Docker Compose v2)
- curl

### Step 1: Clean Start

```bash
# Remove any existing containers
docker-compose down -v

# Clean up data directories
rm -rf ./data ./autoload
```

### Step 2: Start Containers

```bash
docker-compose up -d
```

Expected output:
```
Creating network "scubascore-network"
Creating scubascore ... done
```

### Step 3: Verify Health Check

Wait for the container to be healthy (up to 30 seconds):

```bash
# Check health endpoint
curl http://localhost:5000/health
```

Expected response:
```json
{"status": "ok"}
```

Verify container health status:
```bash
docker inspect --format='{{.State.Health.Status}}' scubascore
```

Expected: `healthy`

### Step 4: Test Score API Endpoint

Post sample compliance data:

```bash
curl -X POST \
  -H "Content-Type: application/json" \
  -d '{
    "services": {
      "AWS": {
        "controls": [
          {"id": "aws-001", "status": "pass"},
          {"id": "aws-002", "status": "pass"},
          {"id": "aws-003", "status": "fail"}
        ]
      },
      "Okta": {
        "controls": [
          {"id": "okta-001", "status": "pass"},
          {"id": "okta-002", "status": "fail"}
        ]
      }
    }
  }' \
  http://localhost:5000/score
```

Expected response includes:
- `overall_score`: A calculated score (0-100)
- `per_service`: Breakdown by service
- `top_failures`: List of failed controls

### Step 5: Verify Database Persistence

Check that the database file was created:

```bash
ls -la ./data/scubascore.db
```

Expected: Database file exists and has non-zero size

Retrieve score history:
```bash
curl http://localhost:5000/score
```

Expected: Array with at least one score record

### Step 6: Test Data Persistence Across Restart

Restart the container:

```bash
docker-compose restart
```

Wait for health check:
```bash
curl http://localhost:5000/health
```

Retrieve score history again:
```bash
curl http://localhost:5000/score
```

**Critical Verification**: The score history should still contain the previously posted data, proving that data persists across container restarts.

### Step 7: Verify Volume Mounts

Check database volume:
```bash
docker-compose exec scubascore ls -la /app/data/scubascore.db
```

Check autoload volume:
```bash
docker-compose exec scubascore ls -la /app/autoload
```

Check configuration files:
```bash
docker-compose exec scubascore cat /app/weights.yaml
```

All commands should complete successfully.

### Step 8: Test Autoload Functionality

Create a test JSON file in the autoload directory:

```bash
mkdir -p ./autoload
echo '{"services":{"Test":{"controls":[{"id":"test-001","status":"pass"}]}}}' > ./autoload/test.json
```

Wait for the autoloader to process it (default interval: 60 seconds, or check container logs):

```bash
docker-compose logs -f scubascore
```

Look for log message: `Processing autoload file: test.json`

The file should be moved to `./autoload/processed/` after processing.

### Step 9: Verify Environment Variables

Check that environment variables are properly applied:

```bash
docker-compose exec scubascore env | grep FLASK_ENV
docker-compose exec scubascore env | grep DB_NAME
docker-compose exec scubascore env | grep GUNICORN
```

### Step 10: View Container Logs

```bash
docker-compose logs scubascore
```

Check for:
- Gunicorn startup messages
- Worker processes (should be 4 by default)
- No critical errors

### Step 11: Test Browser Access

Open in your browser:
```
http://localhost:5000/
```

Expected: ScubaScore dashboard loads successfully

### Step 12: Clean Up

```bash
docker-compose down
```

Optional - remove volumes completely:
```bash
docker-compose down -v
rm -rf ./data ./autoload
```

## Acceptance Criteria Verification

### ✓ Dockerfile builds successfully with all dependencies

```bash
docker build -t scubascore:test .
```

Expected: Build completes without errors

### ✓ docker-compose.yml provides complete deployment with persistent data

```bash
docker-compose config
```

Expected: Valid YAML configuration output

```bash
docker-compose up -d
docker-compose ps
```

Expected: Container running with status "Up" and "healthy"

### ✓ Production-ready WSGI server (gunicorn) configured

```bash
docker-compose logs scubascore | grep gunicorn
```

Expected: Gunicorn startup messages with 4 workers

### ✓ Environment variables for all configuration options

See Step 9 above - all environment variables should be set

### ✓ Health check endpoint for container orchestration

```bash
curl http://localhost:5000/health
```

Expected: `{"status": "ok"}` with HTTP 200

## Troubleshooting

### Container fails to start

Check logs:
```bash
docker-compose logs scubascore
```

Common issues:
- Port 5000 already in use: Change `PORT` in `.env` file
- Permission issues: Check volume mount permissions

### Health check fails

Increase start period in docker-compose.yml:
```yaml
healthcheck:
  start_period: 30s  # Increase if needed
```

### Database not persisting

Verify volume mount:
```bash
docker-compose config | grep -A 5 volumes
```

Ensure `./data` directory has proper permissions:
```bash
chmod 755 ./data
```

### Autoload directory not working

Check that the directory exists and is mounted:
```bash
docker-compose exec scubascore ls -la /app/autoload
```

Verify watcher is running:
```bash
docker-compose logs scubascore | grep -i watcher
```

## Performance Verification

### Gunicorn Workers

Default configuration: 4 workers

To adjust:
```bash
# In .env file
GUNICORN_WORKERS=8
```

### Resource Usage

Check container resources:
```bash
docker stats scubascore
```

### Response Times

Test API response time:
```bash
time curl http://localhost:5000/health
```

Expected: < 100ms for health check

## Security Verification

### Non-root User

Check process user:
```bash
docker-compose exec scubascore ps aux
```

### Read-only Mounts

Configuration files should be mounted read-only:
```bash
docker-compose config | grep ":ro"
```

### Environment Isolation

Verify production environment:
```bash
docker-compose exec scubascore env | grep FLASK_ENV
```

Expected: `FLASK_ENV=production`

## Production Deployment Checklist

- [ ] Docker image builds successfully
- [ ] Health check endpoint responds
- [ ] API endpoints function correctly
- [ ] Data persists across restarts
- [ ] Volumes mounted correctly
- [ ] Environment variables configured
- [ ] Gunicorn running with multiple workers
- [ ] Container restarts automatically (unless-stopped)
- [ ] Logs are accessible
- [ ] Browser access works
- [ ] Autoload directory processes files
- [ ] Configuration files are mounted

## Next Steps

After successful verification:

1. **Customize Configuration**: Copy `.env.example` to `.env` and adjust settings
2. **Configure Monitoring**: Set up container health monitoring
3. **Set Up Backups**: Configure regular backups of `./data/scubascore.db`
4. **SSL/TLS**: Add reverse proxy (nginx, traefik) for HTTPS
5. **Scaling**: Adjust `GUNICORN_WORKERS` based on server resources
6. **Logging**: Configure log aggregation if needed

## Support

For issues or questions:
- Check container logs: `docker-compose logs scubascore`
- Verify configuration: `docker-compose config`
- Test connectivity: `curl http://localhost:5000/health`
- Review this verification document

---

**Verification Script**: `./test-e2e.sh`
**Configuration**: `.env.example`
**Docker Compose**: `docker-compose.yml`
**Dockerfile**: `Dockerfile`

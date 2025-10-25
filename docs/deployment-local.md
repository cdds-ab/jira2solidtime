# Local Deployment with Docker Compose

This guide covers deploying jira2solidtime locally using Docker Compose for both development and production environments.

## Quick Start (Development)

The simplest way to run jira2solidtime locally is using the included `docker-compose.yml`:

```bash
# 1. Copy example configuration
cp config.json.example config.json

# 2. Edit configuration with your credentials
nano config.json  # or use your preferred editor

# 3. Start the service
docker-compose up -d

# 4. Access the web UI
open http://localhost:8080
```

## Production Setup

For production-grade local deployment, use the enhanced configuration with health checks, proper logging, and restart policies.

### 1. Production Configuration File

Create `docker-compose.prod.yml` with production-optimized settings:

```yaml
version: '3.8'

services:
  app:
    image: cddsab/jira2solidtime:0.1.0
    container_name: jira2solidtime
    restart: unless-stopped
    ports:
      - "8080:8080"
    volumes:
      - ./config.json:/app/config.json:ro
      - app-data:/app/data
    environment:
      - TZ=Europe/Berlin
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8080/"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"

volumes:
  app-data:
    driver: local
```

### 2. Start Production Environment

```bash
docker-compose -f docker-compose.prod.yml up -d
```

### 3. Verify Health Status

```bash
# Check container status
docker ps

# Check health status
docker inspect jira2solidtime | grep -A 10 Health

# View logs
docker-compose -f docker-compose.prod.yml logs -f
```

## Configuration Management

### Environment-Specific Configurations

For different environments (dev, staging, prod), use separate configuration files:

```bash
project/
├── config.dev.json      # Development settings
├── config.staging.json  # Staging settings
├── config.prod.json     # Production settings
└── docker-compose.prod.yml
```

Update the volume mount in `docker-compose.prod.yml`:

```yaml
volumes:
  - ./config.prod.json:/app/config.json:ro
```

### Secrets Management

**Never commit credentials to version control!**

Options for managing secrets:

#### Option 1: Environment Variables (Not recommended for this app)

The current application uses `config.json` for configuration. If you need environment variables, consider extending the app or using a secrets manager.

#### Option 2: Docker Secrets (Recommended)

For Docker Swarm deployments:

```bash
# Create secret
echo '{"jira": {"api_token": "secret"}}' | docker secret create jira_config -

# Use in docker-compose
secrets:
  jira_config:
    external: true
```

#### Option 3: External Config Management

Use tools like:
- **Vault** by HashiCorp
- **Azure Key Vault** (if deploying to Azure)
- **AWS Secrets Manager**

## Persistent Data

### Backup Strategy

The application stores data in two locations:

1. **Configuration**: `config.json` (should be backed up separately)
2. **Runtime Data**: `/app/data` directory (contains worklog mappings and sync history)

**Backup the data volume:**

```bash
# Create backup
docker run --rm \
  -v jira2solidtime_app-data:/data \
  -v $(pwd)/backups:/backup \
  alpine tar czf /backup/data-backup-$(date +%Y%m%d).tar.gz /data

# Restore backup
docker run --rm \
  -v jira2solidtime_app-data:/data \
  -v $(pwd)/backups:/backup \
  alpine tar xzf /backup/data-backup-20251024.tar.gz -C /
```

### Volume Management

List all volumes:

```bash
docker volume ls | grep jira2solidtime
```

Inspect volume:

```bash
docker volume inspect jira2solidtime_app-data
```

Remove volume (⚠️ deletes all data):

```bash
docker-compose down -v
```

## Logging

### View Logs

```bash
# Follow logs
docker-compose -f docker-compose.prod.yml logs -f

# View last 100 lines
docker-compose -f docker-compose.prod.yml logs --tail=100

# Filter by service
docker-compose -f docker-compose.prod.yml logs -f app
```

### Log Rotation

The production config includes log rotation:

```yaml
logging:
  driver: "json-file"
  options:
    max-size: "10m"    # Maximum size per file
    max-file: "3"      # Keep 3 rotated files
```

This limits disk usage to ~30MB for logs.

### External Log Aggregation

For centralized logging, consider:

- **ELK Stack** (Elasticsearch, Logstash, Kibana)
- **Grafana Loki**
- **Fluentd**

Example with Loki:

```yaml
logging:
  driver: loki
  options:
    loki-url: "http://loki:3100/loki/api/v1/push"
```

## Performance Tuning

### Resource Limits

Limit CPU and memory usage:

```yaml
services:
  app:
    deploy:
      resources:
        limits:
          cpus: '1.0'
          memory: 512M
        reservations:
          cpus: '0.5'
          memory: 256M
```

### Sync Schedule Optimization

Adjust sync frequency in `config.json`:

```json
{
  "sync": {
    "schedule": "*/10 * * * *",  // Every 10 minutes
    "days_back": 30
  }
}
```

**Recommendations:**
- **High-frequency**: `*/5 * * * *` (every 5 min) - for real-time needs
- **Standard**: `0 * * * *` (hourly) - balanced approach
- **Low-frequency**: `0 8 * * *` (daily at 8 AM) - minimal overhead

## Troubleshooting

### Common Issues

#### 1. Container Won't Start

**Check logs:**
```bash
docker logs jira2solidtime
```

**Common causes:**
- Invalid `config.json` syntax
- Missing API credentials
- Port 8080 already in use

**Solution:**
```bash
# Check port usage
lsof -i :8080

# Use different port
docker-compose -f docker-compose.prod.yml up -d \
  --scale app=1 \
  -p 8081:8080
```

#### 2. Sync Errors

**Symptoms:** Failed sync attempts in web UI

**Debug steps:**
1. Check API credentials in `config.json`
2. Verify network connectivity:
   ```bash
   docker exec jira2solidtime curl -I https://api.tempo.io
   ```
3. Check logs for detailed error messages

#### 3. Permission Denied on Volumes

**Error:** `Permission denied: /app/data`

**Solution:** Ensure correct file ownership

```bash
# Check volume location
docker volume inspect jira2solidtime_app-data

# Fix permissions (if needed)
docker run --rm -v jira2solidtime_app-data:/data alpine chown -R 1000:1000 /data
```

#### 4. High Memory Usage

**Check memory usage:**
```bash
docker stats jira2solidtime
```

**Reduce memory footprint:**
- Decrease `days_back` in config
- Increase sync interval
- Add resource limits (see Performance Tuning)

### Health Check Failures

If health checks consistently fail:

```bash
# Manual health check
docker exec jira2solidtime curl -f http://localhost:8080/

# Check if web service is running
docker exec jira2solidtime ps aux | grep python
```

## Updates and Maintenance

### Updating the Application

```bash
# Pull latest image
docker pull cddsab/jira2solidtime:latest

# Restart with new image
docker-compose -f docker-compose.prod.yml down
docker-compose -f docker-compose.prod.yml up -d

# Verify version
docker exec jira2solidtime python -c "import jira2solidtime; print(jira2solidtime.__version__)"
```

### Cleanup Old Images

```bash
# Remove unused images
docker image prune -a
```

## Monitoring

### Basic Health Monitoring

Create a simple monitoring script `monitor.sh`:

```bash
#!/bin/bash

# Check if container is running
if ! docker ps | grep -q jira2solidtime; then
    echo "ERROR: Container not running"
    # Send alert (email, Slack, etc.)
    exit 1
fi

# Check health status
HEALTH=$(docker inspect --format='{{.State.Health.Status}}' jira2solidtime)
if [ "$HEALTH" != "healthy" ]; then
    echo "WARNING: Container health is $HEALTH"
    exit 1
fi

echo "OK: Container is healthy"
```

Run via cron:
```bash
# Check every 5 minutes
*/5 * * * * /path/to/monitor.sh
```

### Advanced Monitoring

For production environments, integrate with monitoring tools:

- **Prometheus** + **Grafana**: Metrics and dashboards
- **Uptime Kuma**: Simple uptime monitoring
- **Healthchecks.io**: Dead man's switch for scheduled tasks

## Security Considerations

### Local Security Best Practices

1. **Never expose to internet** without authentication
2. **Bind to localhost only** for extra security:
   ```yaml
   ports:
     - "127.0.0.1:8080:8080"
   ```
3. **Use read-only config** (`:ro` flag on volume mount)
4. **Regular updates**: Pull latest images weekly
5. **Scan for vulnerabilities**:
   ```bash
   docker scan cddsab/jira2solidtime:latest
   ```

### Network Isolation

For added security, use a custom network:

```yaml
networks:
  jira2solidtime:
    driver: bridge
    internal: true  # No external access

services:
  app:
    networks:
      - jira2solidtime
```

## Next Steps

- For Azure deployment, see [Azure Deployment Guide](deployment-azure.md)
- For development setup, see main [README](../README.md)
- Report issues at [GitHub Issues](https://github.com/cdds-ab/jira2solidtime/issues)

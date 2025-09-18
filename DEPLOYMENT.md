# Deployment Guide

This guide covers the different ways to deploy jira2solidtime in production.

## Deployment Options

### 1. Docker - App Only (Lightweight)

Minimal Docker deployment with just the application:

```bash
# Pull the lightweight image
docker run cddsab/jira2solidtime:latest-app --help

# Or build locally
docker build -f docker/Dockerfile.app -t jira2solidtime:app .
docker run jira2solidtime:app --help
```

**Use case**: Simple production deployments, microservices architecture.

### 2. Docker Compose - App + Scheduler

Production-ready deployment with automatic scheduling:

```bash
# Download compose file
curl -O https://raw.githubusercontent.com/cddsab/jira2solidtime/main/compose/docker-compose.app.yml

# Create environment file
cp .env.template .env
# Edit .env with your credentials

# Deploy
docker-compose -f docker-compose.app.yml up -d
```

Features:
- Automatic sync scheduling (daily at 8 AM)
- Persistent data volumes
- Health checks
- Restart policies

**Use case**: Production deployments without monitoring needs.

### 3. Docker Compose - Full Stack (Production)

Complete deployment with monitoring and alerting:

```bash
# Clone repository or download compose file
git clone https://github.com/cddsab/jira2solidtime.git
cd jira2solidtime

# Create environment file
cp .env.template .env
# Edit .env with your credentials

# Deploy full stack
docker-compose up -d
```

Features:
- Application with automatic scheduling
- Prometheus metrics collection
- Grafana dashboards
- Alertmanager with Telegram notifications
- Performance monitoring
- Health checks and auto-recovery

**Use case**: Production deployments requiring monitoring and alerting.

### 4. Development Setup

Development environment with hot-reload and debugging:

```bash
# Clone repository
git clone https://github.com/cddsab/jira2solidtime.git
cd jira2solidtime

# Create environment file
cp .env.template .env
# Edit .env with your credentials

# Start development environment
docker-compose -f compose/docker-compose.dev.yml up -d

# Access services
# - Prometheus: http://localhost:9090
# - Grafana: http://localhost:3000 (admin/admin)

# Execute commands in development container
docker exec -it jira2solidtime-dev bash
uv run jira2solidtime sync
```

Features:
- Source code mounted for hot-reload
- Debug logging enabled
- Development tools included
- Monitoring stack for testing

## Environment Configuration

All deployment methods use environment variables for configuration. Create a `.env` file:

```bash
# Required - Jira Configuration
JIRA_BASE_URL=https://yourcompany.atlassian.net
JIRA_USER_EMAIL=your.email@company.com
JIRA_API_TOKEN=your_jira_api_token
JIRA_ORGANISATION_ID=your_jira_org_id

# Required - Solidtime Configuration
SOLIDTIME_BASE_URL=https://app.solidtime.io
SOLIDTIME_API_TOKEN=your_solidtime_api_token
SOLIDTIME_ORGANIZATION_ID=your_solidtime_org_id

# Required - Tempo Configuration
TEMPO_API_TOKEN=your_tempo_api_token

# Optional - Project Mapping
PROJECT_MAPPINGS=JIRA_KEY|Solidtime Project Name,ANOTHER_KEY|Another Project

# Optional - Sync Configuration
SYNC_DAYS_BACK=30
SYNC_SCHEDULE=0 8 * * *  # Daily at 8 AM

# Optional - Notifications (for full stack deployment)
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id
TEAMS_WEBHOOK_URL=your_teams_webhook

# Optional - Filtering
FILTER_USER_EMAIL=specific.user@company.com
FILTER_PROJECT_KEYS=PROJECT1,PROJECT2
```

## Health Checks

All Docker deployments include health checks:

```bash
# Check application health
docker exec jira2solidtime-app jira2solidtime version

# Check container health
docker ps --filter "name=jira2solidtime"

# View logs
docker logs jira2solidtime-app
```

## Monitoring (Full Stack Only)

Access monitoring services:

- **Prometheus**: http://localhost:9090
  - Metrics collection and querying
  - Target health status

- **Grafana**: http://localhost:3000
  - Username: admin
  - Password: admin
  - Pre-configured dashboards for jira2solidtime metrics

- **Alertmanager**: http://localhost:9093
  - Alert routing and notification management
  - Telegram integration for critical alerts

## Scaling Considerations

For high-volume environments:

1. **Increase resources**: Adjust `MAX_WORKERS` and `BATCH_SIZE`
2. **Optimize sync frequency**: Reduce `SYNC_DAYS_BACK` for more frequent syncs
3. **Database persistence**: Use external volumes for data persistence
4. **Load balancing**: Deploy multiple app instances behind a load balancer

## Security Best Practices

1. **Environment Variables**: Never commit `.env` files to version control
2. **API Tokens**: Use least-privilege tokens with appropriate scopes
3. **Network Security**: Use Docker networks to isolate services
4. **Updates**: Regularly update to latest versions for security patches
5. **Monitoring**: Enable alerting for failed syncs and authentication errors

## Troubleshooting

Common issues and solutions:

1. **Authentication Errors**: Verify API tokens and URLs
2. **Permission Denied**: Check Docker permissions and user mappings
3. **Sync Failures**: Review logs and increase `API_TIMEOUT`
4. **Memory Issues**: Reduce `BATCH_SIZE` and `MAX_WORKERS`

For detailed troubleshooting, check the application logs:

```bash
# Docker Compose
docker-compose logs jira2solidtime

# Docker
docker logs jira2solidtime-app

# Local installation
jira2solidtime --help
```
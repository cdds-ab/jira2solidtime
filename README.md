# jira2solidtime

[![GitHub Release](https://img.shields.io/github/v/release/cdds-ab/jira2solidtime?include_prereleases&style=flat-square)](https://github.com/cdds-ab/jira2solidtime/releases)
[![Docker Hub](https://img.shields.io/docker/v/cddsab/jira2solidtime?style=flat-square&logo=docker)](https://hub.docker.com/r/cddsab/jira2solidtime)
[![CI/CD](https://img.shields.io/github/actions/workflow/status/cdds-ab/jira2solidtime/ci.yml?branch=master&style=flat-square&logo=github)](https://github.com/cdds-ab/jira2solidtime/actions)
[![Docker Pulls](https://img.shields.io/docker/pulls/cddsab/jira2solidtime?style=flat-square&logo=docker)](https://hub.docker.com/r/cddsab/jira2solidtime)
[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg?style=flat-square)](https://opensource.org/licenses/Apache-2.0)
[![Python](https://img.shields.io/badge/Python-3.10%2B-blue?style=flat-square&logo=python)](https://www.python.org/)

Synchronize time tracking data from Jira Tempo to Solidtime with a modern CLI interface and production-ready monitoring.

## Features

- 🔄 Intelligent worklog synchronization between Jira Tempo and Solidtime
- 📊 Rich terminal interface with progress indicators and formatted tables
- 🎯 Jira-style duration formatting (2h 30m instead of 2.8h)
- 🔍 Change detection with visual indicators (UPDATE operations in yellow)
- 🛡️ Type-safe service layer architecture with comprehensive error handling
- 📈 **Production monitoring** with Prometheus, Grafana, and Alertmanager
- 🔔 **Real-time notifications** via Telegram for critical issues
- 🐳 **Docker-ready** with complete observability stack
- 🔐 **Security-first** approach with no hardcoded credentials

## Installation

### Docker (Recommended)

**Quick Start - Application Only:**
```bash
# Download minimal compose file for latest release
LATEST_VERSION=$(curl -s https://api.github.com/repos/cdds-ab/jira2solidtime/releases/latest | grep tag_name | cut -d '"' -f 4)
curl -O https://github.com/cdds-ab/jira2solidtime/releases/download/${LATEST_VERSION}/docker-compose.app.yml

# Configure environment
cp .env.template .env
# Edit .env with your API credentials

# Start application
docker compose -f docker-compose.app.yml up -d
```

**Full Stack with Monitoring:**
```bash
# Download full compose file for latest release
LATEST_VERSION=$(curl -s https://api.github.com/repos/cdds-ab/jira2solidtime/releases/latest | grep tag_name | cut -d '"' -f 4)
curl -O https://github.com/cdds-ab/jira2solidtime/releases/download/${LATEST_VERSION}/docker-compose.yml

# Configure environment
cp .env.template .env
# Edit .env with your API credentials and notification settings

# Start full stack
docker compose up -d
```

**Alternative: Use latest Docker images directly:**
```bash
# App-only with latest release
docker run --rm cddsab/jira2solidtime:latest-app --help

# Or specify exact version from badge above
docker run --rm cddsab/jira2solidtime:v0.1.0-beta.2-app --help
```

### Development Installation

```bash
uv sync
```

## Quick Start

1. **Install dependencies**:
   ```bash
   uv sync
   ```

2. **Configure environment** (copy `.env.template` to `.env`):
   ```bash
   # Required API credentials
   TEMPO_API_TOKEN=your-tempo-token
   SOLIDTIME_API_TOKEN=your-solidtime-token
   SOLIDTIME_ORGANIZATION_ID=your-org-id
   JIRA_BASE_URL=https://your-domain.atlassian.net
   SOLIDTIME_BASE_URL=https://your-solidtime-instance.com

   # Optional: Sync configuration
   SYNC_DAYS_BACK=30
   ```

3. **Configure project mapping** in `config/mapping_rules.yaml`:
   ```yaml
   project_mappings:
     "JIRA-KEY": "Solidtime Project Name"
   ```

## Usage

### Sync worklogs

**Using Docker:**
```bash
# Sync current month (dry run)
docker run --rm -v ./config:/app/config cddsab/jira2solidtime:0.1.0-beta-app sync --dry-run

# Sync specific date range
docker run --rm -v ./config:/app/config cddsab/jira2solidtime:0.1.0-beta-app sync --from 2024-01-01 --to 2024-01-31
```

**Using uv (development):**
```bash
# Sync current month (dry run)
uv run jira2solidtime sync --dry-run

# Sync specific date range
uv run jira2solidtime sync --from 2024-01-01 --to 2024-01-31

# Sync specific month
uv run jira2solidtime sync --month 2024-01

# Filter by projects
uv run jira2solidtime sync --projects "PROJ1,PROJ2"

# Perform actual sync (remove --dry-run)
uv run jira2solidtime sync --from 2024-01-01 --to 2024-01-31
```

### Debug mode
```bash
uv run jira2solidtime --debug sync --dry-run
```

## Development

### Code quality
```bash
uv run ruff check --fix .
uv run ruff format .
uv run mypy .
```

### Testing
```bash
uv run pytest
```

### Releases
```bash
# Check current version
uv run jira2solidtime version

# Create a new release (run from project root)
./scripts/release.sh
```

## Architecture

The application follows a clean **service layer architecture**:

```
├── cli/           # Rich terminal interface with progress indicators
├── services/      # Core business logic (SyncService, HealthChecker)
├── api/           # External API clients (Tempo, Jira, Solidtime)
├── sync/          # Synchronization logic and issue comparison
├── utils/         # Utilities (mapping, logging, metrics export)
└── monitoring/    # Observability stack configuration
```

### Key Components

- **SyncService**: Orchestrates the entire synchronization workflow
- **IssueComparator**: Determines what needs syncing using mapping-file approach
- **WorklogMapping**: Handles CSV-based worklog persistence and conflict resolution
- **HealthChecker**: Monitors API availability for alerting
- **MetricsExporter**: Exports Prometheus metrics for monitoring

### Design Principles

- 🎯 **Single responsibility** - each service has a clear, focused purpose
- 🔄 **Dependency injection** - testable and flexible architecture
- 📊 **Observable** - comprehensive metrics and logging
- 🛡️ **Type-safe** - full type hints with mypy validation

## Production Monitoring

This project includes a comprehensive monitoring stack with Prometheus, Grafana, and Alertmanager.

### Setup Monitoring

1. **Configure notifications** (copy `.env.template` to `.env` and fill in values):
   ```bash
   # Required for Telegram notifications
   TELEGRAM_BOT_TOKEN=your-telegram-bot-token
   TELEGRAM_CHAT_ID=your-telegram-chat-id

   # Optional for Teams notifications
   TEAMS_WEBHOOK_URL=your-teams-webhook-url
   ```

2. **Generate Alertmanager configuration**:
   ```bash
   # Generate secure configuration from template
   ./generate-alertmanager-config.sh
   ```

3. **Start monitoring stack**:
   ```bash
   docker compose up -d
   ```

### Monitoring Services

- **Grafana**: http://localhost:3000 (admin/admin) - Real-time dashboards
- **Prometheus**: http://localhost:9090 - Metrics collection and alerting
- **Alertmanager**: http://localhost:9093 - Notification management
- **Metrics endpoint**: http://localhost:8000/metrics - Application metrics

### Alert Management

**Alerts resolve automatically** when issues are fixed. No manual intervention required!

- **Automatic resolution**: Alerts disappear when metrics return to normal
- **Telegram notifications**: Get "✅ RESOLVED" messages when problems are fixed
- **Optional silencing**: Use Alertmanager UI at http://localhost:9093 for maintenance windows

**Common alert types:**
- 🚨 **Critical**: Sync failures, API outages (immediate notification)
- ⚠️ **Warning**: Performance issues, stale data (2min delay)

### Security Notes

- 🔐 **No hardcoded credentials** - all secrets in environment variables
- 🛡️ **Template-based configuration** - generate configs from `.template` files
- 🚫 **Git-ignored secrets** - generated `alertmanager.yml` never committed
- 🔄 **Regenerate on change** - run `./generate-alertmanager-config.sh` when updating credentials

## License

Copyright 2025 CDDS AB

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
# jira2solidtime

Synchronize time tracking data from Jira Tempo to Solidtime with a modern CLI interface.

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
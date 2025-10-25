# jira2solidtime

[![GitHub Release](https://img.shields.io/github/v/release/cdds-ab/jira2solidtime?include_prereleases&style=flat-square)](https://github.com/cdds-ab/jira2solidtime/releases)
[![Docker Hub](https://img.shields.io/docker/v/cddsab/jira2solidtime?style=flat-square&logo=docker)](https://hub.docker.com/r/cddsab/jira2solidtime)
[![CI/CD](https://img.shields.io/github/actions/workflow/status/cdds-ab/jira2solidtime/ci.yml?branch=master&style=flat-square&logo=github)](https://github.com/cdds-ab/jira2solidtime/actions)
[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg?style=flat-square)](https://opensource.org/licenses/Apache-2.0)
[![Python](https://img.shields.io/badge/Python-3.11%2B-blue?style=flat-square&logo=python)](https://www.python.org/)

Minimal daemon for synchronizing time tracking data from Jira Tempo to Solidtime.

## Features

- 🔄 **Intelligent Synchronization**: CREATE/UPDATE/DELETE operations with change detection
- 📝 **Rich Descriptions**: Includes Jira issue summaries and worklog comments
- 🔍 **Deduplication**: Prevents duplicate entries with persistent mapping
- 🛡️ **Recovery**: Automatically recreates manually deleted entries (404 detection)
- 🕐 **Scheduled Sync**: Configurable cron expressions for automatic syncing
- 🌐 **Web UI**: Simple dashboard for configuration and sync history
- 📊 **History Tracking**: SQLite database for persistent sync history
- 🔐 **Security-First**: No hardcoded credentials, security scanning with pre-commit hooks
- 🐳 **Docker Ready**: Minimal deployment (~50MB image)
- ⚡ **Simple Codebase**: Maintainable architecture (~800 lines)

## Quick Start

### Prerequisites

- Docker & Docker Compose (recommended)
- Or: Python 3.11+ with uv

### Docker Setup (Recommended)

1. **Create configuration:**
```bash
cp config.json.example config.json
# Edit config.json with your API credentials and mappings
```

2. **Start the daemon:**
```bash
docker-compose up -d
```

3. **Access web UI:**
- Dashboard: http://localhost:8080
- Sync history and statistics
- Manual sync trigger

### Local Development

1. **Install dependencies:**
```bash
uv sync
```

2. **Configure:**
```bash
cp config.json.example config.json
# Fill in your API credentials
```

3. **Run daemon:**
```bash
uv run src/jira2solidtime/main.py
```

## Deployment

### Local Development

For local testing and development, use Docker Compose:

```bash
docker-compose up -d
```

For production-ready local deployment with health checks, logging, and restart policies, see the [Local Deployment Guide](docs/deployment-local.md).

### Production Deployment

#### Azure App Service

Deploy as a managed web app with auto-scaling, SSL, and monitoring:

**Quick deploy with Azure CLI:**
```bash
# Create web app
az webapp create \
  --resource-group rg-jira2solidtime \
  --plan plan-jira2solidtime \
  --name jira2solidtime-app \
  --deployment-container-image-name cddsab/jira2solidtime:0.1.0

# Configure app
az webapp config appsettings set \
  --resource-group rg-jira2solidtime \
  --name jira2solidtime-app \
  --settings WEBSITES_PORT=8080
```

**Infrastructure as Code with Terraform:**

See the [Azure Deployment Guide](docs/deployment-azure.md) for complete setup with both Azure CLI and Terraform examples.

#### Cost Estimation

- **Local (Docker Compose)**: Free (own hardware)
- **Azure App Service (B1)**: ~12€/month

## Configuration

Configuration uses a single `config.json` file:

```json
{
  "jira": {
    "base_url": "https://your-domain.atlassian.net",
    "user_email": "user@company.com",
    "api_token": "your-token"
  },
  "tempo": {
    "api_token": "your-tempo-token"
  },
  "solidtime": {
    "base_url": "https://solidtime.yourinstance.com",
    "api_token": "your-solidtime-token",
    "organization_id": "org-id"
  },
  "sync": {
    "schedule": "0 8 * * *",
    "days_back": 30
  },
  "mappings": {
    "JIRA-KEY": "Solidtime Project Name"
  },
  "web": {
    "port": 8080
  }
}
```

### Configuration Fields

| Field | Description |
|-------|-------------|
| `jira.base_url` | Your Jira instance URL |
| `jira.user_email` | Jira user email for API authentication |
| `jira.api_token` | Jira API token |
| `tempo.api_token` | Tempo API authentication token |
| `solidtime.base_url` | Solidtime instance URL |
| `solidtime.api_token` | Solidtime API token |
| `solidtime.organization_id` | Solidtime organization ID |
| `sync.schedule` | Cron expression for sync timing (default: daily 8 AM) |
| `sync.days_back` | Days to sync back (default: 30) |
| `mappings` | Map Jira project keys to Solidtime project names |
| `web.port` | Web UI port (default: 8080) |

## Web UI

The dashboard provides:

- **Configuration**: View and edit sync settings
- **Sync History**: Last 50 syncs with status, duration, and entry counts
- **Statistics**: Total syncs, success rate, time entries created
- **Manual Sync**: Trigger sync immediately

## How It Works

### Sync Process

1. **Fetch Worklogs**: Retrieves worklogs from Tempo API for configured time range
2. **Enrich Data**: Fetches Jira issue summaries (with caching to reduce API calls)
3. **Build Descriptions**: Creates formatted descriptions: `ISSUE-KEY: Summary - Comment`
4. **Intelligent Sync**:
   - **CREATE**: New worklogs are created in Solidtime
   - **UPDATE**: Changed worklogs are updated (duration, description, or date changed)
   - **DELETE**: Worklogs removed from Tempo are deleted from Solidtime
   - **SKIP**: Unchanged entries are left alone (after existence check)
5. **Track Mappings**: Maintains persistent mapping between Tempo and Solidtime entry IDs
6. **Recovery**: Detects manually deleted entries (404) and recreates them automatically

### Change Detection

The sync only updates entries when:
- Duration has changed
- Description has changed (issue summary or worklog comment)
- Date/time has changed

Unchanged entries are skipped to minimize API calls, but existence is still verified via UPDATE to detect manual deletions.

### Deduplication

Each Tempo worklog ID is mapped to its corresponding Solidtime time entry ID in `data/worklog_mapping.json`. This ensures:
- No duplicate entries are created
- Updates target the correct entry
- Deleted worklogs can be cleaned up

## Development

### Code Quality

```bash
# Format code
uv run ruff format src/

# Lint
uv run ruff check src/

# Type checking
uv run mypy src/
```

### Project Structure

```
src/jira2solidtime/
├── config.py          # JSON configuration loader
├── daemon.py          # APScheduler background daemon
├── history.py         # SQLite history tracking
├── main.py            # Application entrypoint
├── api/               # API clients (Tempo, Jira, Solidtime)
├── sync/              # Synchronization logic
└── web/               # Flask web UI
```

## Architecture

- **Service layer**: Clean separation of concerns
- **Daemon**: APScheduler for reliable scheduling
- **History**: SQLite for persistent tracking
- **Web UI**: Simple Flask application
- **Configuration**: Single JSON file, no environment variables needed

## License

Licensed under the Apache License 2.0. See [LICENSE](LICENSE) file for details.

## Support

For issues, questions, or contributions, please visit the [GitHub repository](https://github.com/cdds-ab/jira2solidtime).

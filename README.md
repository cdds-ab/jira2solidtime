# jira2solidtime

[![GitHub Release](https://img.shields.io/github/v/release/cdds-ab/jira2solidtime?include_prereleases&style=flat-square)](https://github.com/cdds-ab/jira2solidtime/releases)
[![Docker Hub](https://img.shields.io/docker/v/cddsab/jira2solidtime?style=flat-square&logo=docker)](https://hub.docker.com/r/cddsab/jira2solidtime)
[![CI/CD](https://img.shields.io/github/actions/workflow/status/cdds-ab/jira2solidtime/ci.yml?branch=master&style=flat-square&logo=github)](https://github.com/cdds-ab/jira2solidtime/actions)
[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg?style=flat-square)](https://opensource.org/licenses/Apache-2.0)
[![Python](https://img.shields.io/badge/Python-3.11%2B-blue?style=flat-square&logo=python)](https://www.python.org/)

Minimal daemon for synchronizing time tracking data from Jira Tempo to Solidtime.

## Features

- 🔄 Intelligent worklog synchronization between Jira Tempo and Solidtime
- 🕐 Scheduled synchronization with configurable cron expressions
- 🌐 Simple web UI for configuration and sync history
- 📊 Persistent history tracking with SQLite
- 🔐 Security-first approach with no hardcoded credentials
- 🐳 Minimal Docker deployment (~50MB image)
- ⚡ Simple, maintainable codebase (~800 lines)

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

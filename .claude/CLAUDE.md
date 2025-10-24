# jira2solidtime - Project Development Guidelines

## 🎯 Vision
A minimal, no-bloat daemon tool that synchronizes time tracking from Jira Tempo to Solidtime.
Only core functionality: sync, simple web UI for config + history, nothing else.

## 📦 Dependencies Management
- Use `uv` for all dependency management (not pip)
- Keep dependencies minimal: requests, apscheduler, flask only
- Update `pyproject.toml`, never create requirements.txt

## 💬 Git Workflow
- **Commits**: ALWAYS use Conventional Commits format (REQUIRED!)
  - `feat: add new feature`
  - `fix: resolve bug`
  - `refactor: restructure code`
  - `docs: update documentation`
  - `chore: maintenance tasks`
  - Breaking changes: `feat!: breaking change`
  - **IMPORTANT**: NO "Generated with Claude Code" footers or AI mentions in commit messages!
  - Keep commit messages clean, professional, and focused on WHAT changed
- **Branches**: Work directly on `main`/`master`, no feature branches
- **Releases**: Semantic Versioning via release-please (automatic)

## 🔍 Code Quality Standards
Before every commit, run:
```bash
uv run ruff format .      # Auto-format code
uv run ruff check --fix . # Lint + auto-fix
uv run mypy .             # Type checking
```

## 🛡️ Security & Data Protection
**CRITICAL**: Never commit customer-specific data!
- **config.json**: NEVER commit (contains all secrets, tokens, customer mappings)
- **data/ directory**: NEVER commit ANY files (databases, mappings, etc.)
- **Hardcoded values**: NEVER hardcode organization IDs, URLs, tokens, mappings
- **All customer data**: Must ONLY exist in config.json (gitignored)

## 🔐 Pre-commit Hooks
Security-first approach only:
- `bandit` - Security vulnerability scanner
- `detect-secrets` - Credential detection
NO other hooks. Keep it simple.

## 🏗️ Architecture Principles
- **Simplicity First**: No unnecessary abstractions
- **Single Responsibility**: Each module does one thing well
- **Minimal Code**: ~800 lines total, not 3000+
- **No Hidden Magic**: Explicit over implicit

## 🌐 Code Structure
```
src/jira2solidtime/
├── main.py          # Entrypoint (daemon startup)
├── config.py        # JSON config loader (~50 lines)
├── daemon.py        # Background scheduler
├── history.py       # SQLite sync history
├── api/
│   ├── tempo.py     # Tempo API client
│   ├── solidtime.py # Solidtime API client
│   └── jira.py      # Jira API client
├── sync/
│   ├── syncer.py    # Core sync orchestration
│   └── mapper.py    # Project/task mapping
└── web/
    ├── app.py       # Flask web UI
    └── templates/   # HTML templates
```

## 📝 What to Keep/Remove

### ✅ KEEP
- API clients (minimal)
- Sync core logic
- Flask web UI (config + history)
- Docker & docker-compose
- Pipeline (CI/CD minimal)
- pyproject.toml

### ❌ REMOVE
- CLI (except daemon entrypoint)
- Monitoring stack (Prometheus, Grafana, Alertmanager)
- Health checks
- Metrics exporter
- ConfigManager with SQLite for config
- Structured logging (JSON logs)
- Factories & complex abstractions
- Rich terminal UI
- Notifications (Telegram, Teams)

## 🚀 Development Workflow
1. Make changes to code
2. Format: `uv run ruff format .`
3. Lint: `uv run ruff check --fix .`
4. Type-check: `uv run mypy .`
5. Commit with conventional message
6. Push to main
7. Release-please handles versioning automatically

## 📚 Environment Setup
```bash
uv sync              # Install dependencies
uv run main.py      # Start daemon
uv run tests/       # Run tests (if any)
```

## 🐳 Docker
- Single-stage build with uv
- Minimal base: python:3.11-slim
- Config via config.json mounted volume
- Expose port 8080 for web UI

## 📋 Notes
- No spiral or unnecessary features
- Everything in English (code + comments)
- Security checks in pre-commit
- Straightforward release process

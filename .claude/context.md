# Project Status & Context

## 📊 Current State
- **Version**: 0.3.0 (just released)
- **Branch**: main/master
- **Status**: Beginning radical simplification refactor
- **Goal**: Remove all bloat, keep only core sync functionality

## 🎯 What's Happening
Refactoring from complex enterprise tool to minimal daemon:
- Remove: Monitoring stack, CLI, complex config system, health checks, metrics
- Keep: API clients, sync logic, simple web UI, daemon scheduler
- Code reduction: ~3000 → ~800 lines

## ✅ Completed
- Created .claude/ directory with CLAUDE.md and context.md

## 🔄 In Progress
- Building new minimalalistic structure
- Simplifying API clients
- Extracting core sync logic
- Creating minimal Flask web UI

## ⏭️ Next Steps
1. New minimal structure for src/
2. Simplified API clients
3. Core sync orchestration
4. Flask web UI + history
5. APScheduler daemon
6. Clean up old code
7. Update pyproject.toml
8. Configure pre-commit (security-only)
9. Code quality checks (ruff, mypy)
10. Semantic release setup

## 📝 Key Files
- `.claude/CLAUDE.md` - Development guidelines
- `pyproject.toml` - To be simplified
- `config.json` - Will be the only config file
- `src/jira2solidtime/` - Core application
- `Dockerfile` - Will be simplified
- `.github/workflows/` - Minimal CI/CD

## 🛠️ Tools
- **Dependencies**: uv
- **Code Quality**: ruff, mypy, black
- **Security**: bandit, detect-secrets (pre-commit)
- **Container**: Docker with uv
- **Releases**: Semantic versioning via release-please

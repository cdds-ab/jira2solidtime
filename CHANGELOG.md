# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.0-beta.3](https://github.com/cdds-ab/jira2solidtime/compare/v0.1.0-beta.3...v0.2.0-beta.3) (2025-09-19)


### Features

* complete production-ready monitoring and security setup ([e3c4fc8](https://github.com/cdds-ab/jira2solidtime/commit/e3c4fc8e55480de46ee2f8ed1a7f9412cb240a54))


### Bug Fixes

* add explicit GitHub token for release-please ([89e2ae7](https://github.com/cdds-ab/jira2solidtime/commit/89e2ae77026eb1267f1b73b66ce4cba5d5c4d662))
* update to non-deprecated googleapis/release-please-action ([b2370e0](https://github.com/cdds-ab/jira2solidtime/commit/b2370e01de6f02d3d170af0034833a97ba2b40b1))

## [Unreleased]

## [0.1.0-beta] - 2025-09-19

### Added
- Production-ready monitoring stack with Prometheus, Grafana, and Alertmanager
- Real-time Telegram notifications for critical issues
- Docker Compose orchestration for complete observability
- Service layer architecture with comprehensive error handling
- Rich terminal interface with Jira-style duration formatting (2h 30m)
- Change detection with visual indicators for UPDATE operations
- Pre-commit hooks for automated code quality checks
- Semantic versioning and release workflow
- Security-first approach with template-based configuration
- Comprehensive test suite and documentation
- Dependabot configuration for automated dependency updates
- GitHub Actions CI/CD pipeline with security scanning
- Docker multi-stage builds with app-only variant
- Python 3.13 support with backward compatibility

### Changed
- Refactored from monolithic 420-line function to clean service layer
- Improved CLI with progress indicators and formatted tables
- Enhanced error handling and logging throughout
- Updated documentation with architecture overview and setup guides
- Migrated from manual dependency management to automated updates

### Removed
- Obsolete sync_mode configuration options
- Dead code and unused functions
- IDE and tool-specific files from repository
- Hardcoded credentials from source code

### Security
- Integrated bandit security scanning
- Added detect-secrets for credential detection
- Implemented non-root container execution
- Template-based configuration management

## [v0.1.0] - 2024-01-01

### Added
- Initial release
- Basic Jira Tempo to Solidtime synchronization
- CLI interface with Click
- Configuration management
- Worklog mapping and field mapping
- Basic error handling

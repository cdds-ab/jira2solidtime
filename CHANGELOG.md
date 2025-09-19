# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.0-beta.3](https://github.com/cdds-ab/jira2solidtime/compare/v0.1.0-beta.3...v0.2.0-beta.3) (2025-09-19)


### Features

* add comprehensive Docker and YAML security scanning ([2c1727e](https://github.com/cdds-ab/jira2solidtime/commit/2c1727e0a2c0c0fbc48bfdfbbb3a500df4a9fc5e))
* add comprehensive status badges to README ([0cd2ed0](https://github.com/cdds-ab/jira2solidtime/commit/0cd2ed0449b34be9b8687209ea96b0b7fd887bb4))
* simulate feature to establish clean release pattern ([c19ab41](https://github.com/cdds-ab/jira2solidtime/commit/c19ab41becef8556b22e61b0fb12bb5eb5f1f483))
* test clean semantic versioning ([e1d8947](https://github.com/cdds-ab/jira2solidtime/commit/e1d8947d26eff7dcd5caf0a8dc62e2e170ae53df))


### Bug Fixes

* add explicit GitHub token for release-please ([2f029cd](https://github.com/cdds-ab/jira2solidtime/commit/2f029cdd24ddb6e6e8dab61ded80cf7156a9aace))
* disable prerelease mode for clean 0.2.0 release ([15ed11d](https://github.com/cdds-ab/jira2solidtime/commit/15ed11d0c493cc8452cad6902d313026009de2bb))
* hadolint Docker security scan warnings ([0b39a48](https://github.com/cdds-ab/jira2solidtime/commit/0b39a4840d83d0e98708d4eca84e53082c927735))
* update to non-deprecated googleapis/release-please-action ([f43b556](https://github.com/cdds-ab/jira2solidtime/commit/f43b55673a1eab88c522e80f4f67c29d87ee88f2))

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

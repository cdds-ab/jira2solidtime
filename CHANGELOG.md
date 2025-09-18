# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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

### Changed
- Refactored from monolithic 420-line function to clean service layer
- Improved CLI with progress indicators and formatted tables
- Enhanced error handling and logging throughout
- Updated documentation with architecture overview and setup guides

### Removed
- Obsolete sync_mode configuration options
- Dead code and unused functions
- IDE and tool-specific files from repository

## [v0.1.0] - 2024-01-01

### Added
- Initial release
- Basic Jira Tempo to Solidtime synchronization
- CLI interface with Click
- Configuration management
- Worklog mapping and field mapping
- Basic error handling
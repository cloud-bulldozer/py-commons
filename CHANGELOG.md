# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.3.0] - 2026-06-02

### Added
- Added `commons.jira` - Unified JIRA client for Atlassian Cloud and on-premise instances
  - Support for both Cloud (email + API token) and on-premise (username/password) authentication
  - Automatic retry logic with exponential backoff
  - Common query patterns (by status, label, custom JQL)
  - Issue management (create, update, transition, labels, comments)
  - Custom field support
  - Comprehensive error handling

### Removed
- Removed `commons.fmatch` - Library was not being used in any projects

### Changed
- Updated package description to "Common Python libraries for Red Hat tools and automation"
- Changed keywords from performance/scale focused to jira/automation focused
- Simplified dependencies to only include `jira>=3.0.0`

## [0.2.0] - 2026-06-01

### Added
- Initial namespace package structure with `src/commons/`
- Added `commons.fmatch` - Metadata matching library for performance testing
- Modern Python packaging with `pyproject.toml`
- Comprehensive documentation and README files
- GitHub Actions workflows for testing and PyPI publishing

### Changed
- Migrated from `fmatch` package to `py-commons` namespace package
- Updated imports from `fmatch.*` to `commons.fmatch.*`

## [0.1.6] - Previous

Legacy `fmatch` package releases (pre-namespace reorganization).

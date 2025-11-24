# Changelog

## [0.7.2] - 2025-11-24

### 🐛 Bug Fixes

- fix: address linting errors


## [0.7.1] - 2025-11-24

### 🐛 Bug Fixes

- fix: address uv usage in github actions


## [0.7.0] - 2025-11-24

### ✨ Features

- feat: Add MCP server enhancements for static assets and JWT auth
- feat: Add config_schema auto-generation to molecule metadata

### 🔧 Other Changes

- chore: convert this project to uv

## [0.6.7] - 2025-11-21

### 🔧 Other Changes

- chore: bump the devgraph-client

## [0.6.6] - 2025-11-20

### 🐛 Bug Fixes

- fix(mcp): update the extension loading logic


## [0.6.5] - 2025-11-20

### 🐛 Bug Fixes

- fix: suppress warnings and remove unnecessary logging


## [0.6.4] - 2025-11-20

### 🐛 Bug Fixes

- fix: suppress debug logging in release-manifest


## [0.6.3] - 2025-11-19

### 🐛 Bug Fixes

- fix: use stevedore for extension loading


## [0.6.2] - 2025-11-19

### 🐛 Bug Fixes

- fix: update release for better performance


## [0.6.1] - 2025-11-19

### 🐛 Bug Fixes

- fix: restore release-manifest capabilities

### 🔧 Other Changes

- docs: add guide for creating custom molecules

## [0.6.0] - 2025-11-19

### ✨ Features

- feat: unified molecule architecture with dynamic config sources

### 🔧 Other Changes

- chore: bump version to 0.5.0
- chore: bump version to 0.4.0

## [0.5.0] - 2025-11-19

### ✨ Features

- feat: unified molecule architecture with dynamic config sources


## [0.4.0] - 2025-11-19

### ✨ Features

- feat(ci): extract version-specific changelog for GitHub releases
- feat(config): add environment variable override support
- feat(config): improve config source plugin system

### 🐛 Bug Fixes

- fix(ci): move the release creation after complete docker build

### 🔧 Other Changes

- chore: style cleanups
- refactor(release): combine version bump and changelog into single commit

## [0.3.3] - 2025-11-19

### 🐛 Bug Fixes

- fix: remove extra whitespace from changelog
- fix(ci): address failing lint and mypy issues

### 🔧 Other Changes

- chore: bump version to 0.3.2

## [0.3.2] - 2025-11-19

### 🐛 Bug Fixes

- fix(ci): address failing lint and mypy issues


## [0.3.1] - 2025-11-19

### 🐛 Bug Fixes

- fix: remove references to internal extensions


## [0.3.0] - 2025-11-19

### ✨ Features

- feat(discover): allow for alternate config sources via extension

### 🐛 Bug Fixes

- fix(release): update how we calculate last tag

### 🔧 Other Changes

- chore: bump version to 0.2.0

## [0.2.0] - 2025-11-18

### ✨ Features

- feat: add automatic changelog generation to release script
- feat(release): add conventional commits analysis
- feat: add release script for OSS releases

### 🐛 Bug Fixes

- fix(release): trim whitespace from commit counts to prevent integer comparison errors

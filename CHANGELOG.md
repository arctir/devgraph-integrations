# Changelog

## [0.8.2] - 2025-12-09

### 🐛 Bug Fixes

- fix: update devgraph-client for relation metadata

### 🔧 Other Changes

- Add .devgraph.yaml to mark repository as part of devgraph workstream
- chore: update uv.lock
- Fix FOSSA provider to access repository URLs from spec.url field

## [0.8.1] - 2025-11-26

### 🐛 Bug Fixes

- fix: remove unused imports and fix f-string linting errors


## [0.8.0] - 2025-11-26

### ✨ Features

- feat: add relation ownership tracking with metadata and typed specs

### 🐛 Bug Fixes

- fix: prevent infinite retry loop on 404 entity definition errors

### 🔧 Other Changes

- refactor: migrate all providers to use relation ownership tracking
- test: add comprehensive tests for relation ownership and metadata

## [0.7.10] - 2025-11-25

### 🐛 Bug Fixes

- fix: properly convert EntityDefinition to API EntityDefinitionSpec
- fix: use entity_definition.kind instead of entity_definition.spec.kind


## [0.7.9] - 2025-11-25

### 🐛 Bug Fixes

- fix: resolve discovery pod crashes and plugin loading issues


## [0.7.8] - 2025-11-25

### 🐛 Bug Fixes

- fix: do not fail on exception


## [0.7.7] - 2025-11-25

### 🐛 Bug Fixes

- fix: we need to get the discovery provider to hydrate


## [0.7.6] - 2025-11-25

### 🐛 Bug Fixes

- fix: change the stevedore molecules namespace


## [0.7.5] - 2025-11-24

### 🐛 Bug Fixes

- fix: remove unused import


## [0.7.4] - 2025-11-24

### 🐛 Bug Fixes

- fix: auto-detect package name in release-manifest
- fix: use entry point name (FQDN) as molecule key


## [0.7.3] - 2025-11-24

### 🐛 Bug Fixes

- fix: emit FQDN in release manifest molecule names


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

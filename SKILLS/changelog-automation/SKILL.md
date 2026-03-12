---
name: Changelog Automation
description: Consistent release notes from conventional commits with semantic versioning
phase: 6
---

# Changelog Automation

## Changelog Format (Keep a Changelog)

Follow the [Keep a Changelog](https://keepachangelog.com/) convention. Every release entry is organized by change type.

```markdown
# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/),
and this project adheres to [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added
- OAuth2 login with Google provider (#142)

### Fixed
- Race condition on cart quantity update (#287)

## [1.2.0] - 2026-03-10

### Added
- Password reset via email (#130)
- Product search with full-text indexing (#135)

### Changed
- Upgraded Node.js runtime from 18 to 20 (#138)

### Fixed
- Duplicate items appearing in cart on rapid clicks (#125)
- Incorrect tax calculation for international orders (#128)

### Security
- Updated express to 4.19.0 to patch CVE-2026-XXXX (#140)

## [1.1.0] - 2026-02-15

### Added
- User profile page with avatar upload (#110)

[Unreleased]: https://github.com/org/repo/compare/v1.2.0...HEAD
[1.2.0]: https://github.com/org/repo/compare/v1.1.0...v1.2.0
[1.1.0]: https://github.com/org/repo/compare/v1.0.0...v1.1.0
```

### Change Categories

| Category     | Description                                        |
|--------------|----------------------------------------------------|
| Added        | New features                                       |
| Changed      | Changes to existing functionality                  |
| Deprecated   | Features that will be removed in a future release  |
| Removed      | Features that were removed                         |
| Fixed        | Bug fixes                                          |
| Security     | Vulnerability patches                              |

## Semantic Versioning (SemVer)

Version numbers follow the format `MAJOR.MINOR.PATCH`:

| Component | When to Increment                              | Example       |
|-----------|------------------------------------------------|---------------|
| MAJOR     | Breaking changes to the public API             | 1.0.0 -> 2.0.0 |
| MINOR     | New features that are backward-compatible      | 1.0.0 -> 1.1.0 |
| PATCH     | Bug fixes that are backward-compatible         | 1.0.0 -> 1.0.1 |

### Mapping Commit Types to Version Bumps

| Commit Type          | Version Bump |
|----------------------|--------------|
| `feat`               | MINOR        |
| `fix`                | PATCH        |
| `perf`               | PATCH        |
| `BREAKING CHANGE`    | MAJOR        |
| `feat!` / `fix!`     | MAJOR        |
| `chore`, `docs`, etc.| No release   |

## Automated Changelog from Conventional Commits

### Using standard-version

```bash
npm install --save-dev standard-version
```

Add to `package.json`:
```json
{
  "scripts": {
    "release": "standard-version",
    "release:minor": "standard-version --release-as minor",
    "release:major": "standard-version --release-as major",
    "release:dry": "standard-version --dry-run"
  }
}
```

Configuration in `.versionrc.json`:
```json
{
  "types": [
    { "type": "feat", "section": "Added" },
    { "type": "fix", "section": "Fixed" },
    { "type": "perf", "section": "Performance" },
    { "type": "refactor", "section": "Changed", "hidden": false },
    { "type": "chore", "hidden": true },
    { "type": "docs", "hidden": true },
    { "type": "style", "hidden": true },
    { "type": "test", "hidden": true },
    { "type": "ci", "hidden": true },
    { "type": "build", "hidden": true }
  ],
  "commitUrlFormat": "https://github.com/org/repo/commit/{{hash}}",
  "compareUrlFormat": "https://github.com/org/repo/compare/{{previousTag}}...{{currentTag}}"
}
```

### Using release-please (GitHub Action)

```yaml
name: Release

on:
  push:
    branches: [main]

permissions:
  contents: write
  pull-requests: write

jobs:
  release:
    runs-on: ubuntu-latest
    steps:
      - uses: googleapis/release-please-action@v4
        with:
          release-type: node
          changelog-types: >
            [
              {"type":"feat","section":"Added","hidden":false},
              {"type":"fix","section":"Fixed","hidden":false},
              {"type":"perf","section":"Performance","hidden":false},
              {"type":"docs","section":"Documentation","hidden":true},
              {"type":"chore","section":"Miscellaneous","hidden":true}
            ]
```

## Release Process

### Step-by-Step

1. Ensure all changes for the release are merged into `main`.
2. Run the release command: `npm run release` (or let release-please create the PR).
3. Review the generated changelog entry.
4. Push the version commit and tag: `git push --follow-tags origin main`.
5. Create a GitHub Release from the tag.
6. Deploy the tagged version to production.

### Version Bumping

The tool reads commit messages since the last tag and determines the bump:

- If any commit has `BREAKING CHANGE` or `!` in the type: **MAJOR**.
- If any commit is `feat`: **MINOR**.
- Otherwise (only `fix`, `perf`, etc.): **PATCH**.

## Git Tags

Use annotated tags for releases:

```bash
git tag -a v1.2.0 -m "Release v1.2.0"
git push origin v1.2.0
```

Conventions:
- Prefix tags with `v`: `v1.2.0`, not `1.2.0`.
- Never delete or move published tags.
- Use lightweight tags only for temporary or local markers.

## GitHub Releases

Create releases from tags to provide binaries, notes, and a clear history.

```bash
gh release create v1.2.0 \
  --title "v1.2.0" \
  --notes-file CHANGELOG.md \
  --latest
```

Or extract only the relevant section:

```bash
gh release create v1.2.0 \
  --title "v1.2.0" \
  --generate-notes
```

## Quick Reference

| Concern           | Recommendation                                     |
|-------------------|-----------------------------------------------------|
| Changelog format  | Keep a Changelog with Added/Changed/Fixed sections  |
| Versioning        | Semantic Versioning (MAJOR.MINOR.PATCH)             |
| Automation        | standard-version or release-please                  |
| Commit to version | feat=MINOR, fix=PATCH, BREAKING CHANGE=MAJOR       |
| Tags              | Annotated, prefixed with `v`                        |
| GitHub Releases   | Created from tags with changelog excerpt            |
| Hidden types      | chore, docs, style, test, ci, build                 |

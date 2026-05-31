# Changelog

All notable changes to ScubaScore are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project aims to follow [Semantic Versioning](https://semver.org/spec/v2.0.0.html).
Dates are when the change landed on `main`; the project does not yet cut tagged
releases, so versions below map to project milestones rather than git tags.

## [Unreleased]

### Added

- Dependency-free scoring-engine test suite (`test/score.test.cjs`) that extracts
  the engine from the shipped `index.html` at runtime and asserts weight
  resolution, compensating-control credit, per-service and overall scoring, M365
  ingestion, data-quality counts, and failure ranking. Run with `npm test`.
- GitHub Actions CI (`.github/workflows/ci.yml`) that runs the test suite on
  every push and pull request.
- Community-health files: `SECURITY.md` (security policy and threat model), issue
  forms for bugs and features, an issue-template config, a pull-request template,
  `CONTRIBUTING.md`, and this changelog.
- Repository metadata: description, homepage pointing at the live GitHub Pages
  deploy, and discovery topics.

## [1.0.0] - 2026-05-29

The single-file, fully client-side rewrite — ScubaScore's public launch.

### Added

- One-click **demo data** that scores CISA's official ScubaGoggles (Google
  Workspace) and ScubaGear (Microsoft 365) sample reports, bundled inline.
- Reference links to the upstream CISA SCuBA tools.
- Live deployment on GitHub Pages, linked from the README.

### Changed

- **Rewrote ScubaScore as a single, self-contained `index.html`** that runs
  100% in the browser — no server, no build step, no install. All parsing and
  scoring happen locally and assessment data never leaves the page, enforced by
  a strict Content-Security-Policy (`connect-src 'none'`).
- Service-segment matching is now case-insensitive so real uppercase-ID
  ScubaGoggles/ScubaGear exports are attributed to the correct service.

### Removed

- The Flask server, Docker setup, and all server-side components from the
  previous dashboard architecture.

## [0.2.0] - 2026-01-16

The Flask dashboard era, second iteration.

### Added

- Microsoft 365 SCuBA JSON parsing, M365 service weights, and one-click
  switching between GWS and M365 weight profiles.
- A compensating-controls editor in the settings UI.
- Tree / folder-style navigation of scores, an improved empty state with
  onboarding guidance, and lazy-loaded rule details.
- Dockerfile and docker-compose for containerized deployment, plus an
  end-to-end verification script.
- A proper `README.md` and documentation of the scoring algorithm and weight
  precedence rules.

## [0.1.0] - 2025-12-23

### Added

- Initial SCuBA Score Dashboard: a Flask web application with a UI, backend
  scoring engine, and documentation.

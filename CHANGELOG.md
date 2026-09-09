# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/), and this project adheres
to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

- Added a CI workflow that installs dependencies and verifies the app imports cleanly on push/PR. ([#21](https://github.com/TechVibe-Dev/trip-trace-api/pull/21))
- Added `POST /trips/{trip_id}/finalize` (compute and persist distance/speed stats) and `GET /trips/{trip_id}/segments` (slow/fast segment detection) from GPS points. ([#20](https://github.com/TechVibe-Dev/trip-trace-api/pull/20))
- Backport workflow now pushes a dedicated branch instead of using `main` directly as the PR head, so deleting the branch after merge can't delete `main`. ([#19](https://github.com/TechVibe-Dev/trip-trace-api/pull/19))

## [0.2.0] - 8 Sep 2026

### Added

- CRUD endpoints for trips, stops, and gps points. ([#16](https://github.com/TechVibe-Dev/trip-trace-api/pull/16))

## [0.1.0] - 8 Sep 2026

### Added

- Initial FastAPI scaffold: config, database setup, JWT auth (register/login/me), SQLAlchemy models (User, Trip, Stop, GpsPoint).
- Set up Alembic migrations, with the initial migration creating `users`, `trips`, `stops`, `gps_points`. ([#13](https://github.com/TechVibe-Dev/trip-trace-api/pull/13))
- Extended JWT session length from 7 to 180 days. ([#11](https://github.com/TechVibe-Dev/trip-trace-api/pull/11))
- Finalized Trip and Stop schema: added `planned_departure_at`, `desired_arrival_at`, `calculated_arrival_at` to Trip, and split Stop's `arrival_at` into `planned_arrival_at`/`actual_arrival_at`. ([#10](https://github.com/TechVibe-Dev/trip-trace-api/pull/10))
- Automated backport PR creation (`main` → `develop`) after a release/hotfix merge. ([#9](https://github.com/TechVibe-Dev/trip-trace-api/pull/9))

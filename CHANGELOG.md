# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/), and this project adheres
to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

- Fixed `calculate-route`'s "now" fallback still being rejected by Google ("Timestamp must be set to a future time.") — a bare `now()` is often already past by the time it reaches Google's servers, so it now gets a 1-minute buffer. ([#51](https://github.com/TechVibe-Dev/trip-trace-api/pull/51))

## [0.5.2] - 23 Sep 2026

### Fixed

- `calculate-route` failures now include Google's actual error body (reason, message) in the 502 `detail`, instead of just httpx's generic "400 Bad Request" wrapper with no real information. ([#48](https://github.com/TechVibe-Dev/trip-trace-api/pull/48))

## [0.5.1] - 23 Sep 2026

### Fixed

- Fixed `calculate-route` returning 400 when `planned_departure_at` had already passed — Google Routes' `TRAFFIC_AWARE` mode needs a present-or-future departure time, so a past one now falls back to "now", same as when it's unset. ([#45](https://github.com/TechVibe-Dev/trip-trace-api/pull/45))

## [0.5.0] - 23 Sep 2026

### Added

- Validate latitude/longitude ranges (-90/90, -180/180) on `TripCreate`, `StopCreate`, and `GpsPointCreate`. ([#42](https://github.com/TechVibe-Dev/trip-trace-api/pull/42))

### Fixed

- Fixed a speed unit inconsistency: `max_speed`/`min_speed` and segment `avg_speed` were left in m/s (Android's `Location.getSpeed()` unit) while trip `avg_speed` was already km/h — all four are now consistently km/h. ([#41](https://github.com/TechVibe-Dev/trip-trace-api/pull/41))

## [0.4.0] - 18 Sep 2026

### Fixed

- Reject passwords over 72 bytes with a clean validation error on register/login, instead of letting bcrypt crash (needed before bumping bcrypt to 5.x — see #30). ([#33](https://github.com/TechVibe-Dev/trip-trace-api/pull/33))

### Changed

- Configured Dependabot (pip + github-actions), monthly. ([#27](https://github.com/TechVibe-Dev/trip-trace-api/pull/27), [#37](https://github.com/TechVibe-Dev/trip-trace-api/pull/37))
- Updated dependencies (no security advisories in this batch, routine version bumps): bcrypt →5.0.0, pydantic →2.13.5, alembic →1.19.2→1.20.0, psycopg2-binary →2.9.13, uvicorn →0.53.0, sqlalchemy →2.0.53, actions/checkout →7, actions/setup-python →7. ([#28](https://github.com/TechVibe-Dev/trip-trace-api/pull/28), [#29](https://github.com/TechVibe-Dev/trip-trace-api/pull/29), [#30](https://github.com/TechVibe-Dev/trip-trace-api/pull/30), [#31](https://github.com/TechVibe-Dev/trip-trace-api/pull/31), [#32](https://github.com/TechVibe-Dev/trip-trace-api/pull/32), [#34](https://github.com/TechVibe-Dev/trip-trace-api/pull/34), [#35](https://github.com/TechVibe-Dev/trip-trace-api/pull/35), [#36](https://github.com/TechVibe-Dev/trip-trace-api/pull/36), [#38](https://github.com/TechVibe-Dev/trip-trace-api/pull/38))

## [0.3.0] - 9 Sep 2026

### Added

- Integrated Google Routes API (traffic-aware) via `POST /trips/{trip_id}/calculate-route` to compute ETA and route polyline. ([#22](https://github.com/TechVibe-Dev/trip-trace-api/pull/22))
- Added `POST /trips/{trip_id}/finalize` (compute and persist distance/speed stats) and `GET /trips/{trip_id}/segments` (slow/fast segment detection) from GPS points. ([#20](https://github.com/TechVibe-Dev/trip-trace-api/pull/20))
- Added a CI workflow that installs dependencies and verifies the app imports cleanly on push/PR. ([#21](https://github.com/TechVibe-Dev/trip-trace-api/pull/21))

### Changed

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

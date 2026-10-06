# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/), and this project adheres
to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Changed

- Bumped SQLAlchemy from 2.0.53 to 2.1.3. SQLAlchemy 2.1 maps a bare `postgresql://` URL to the `psycopg` (v3) driver instead of `psycopg2`, which made the app fail to start; `DATABASE_URL` is now normalized to `postgresql+psycopg2://` when it has no explicit driver, so existing env vars keep working. ([#81](https://github.com/TechVibe-Dev/trip-trace-api/pull/81))

## [0.11.0] - 30 Sep 2026

### Changed

- `POST /trips/{id}/recalculate-eta` stops calling Google Routes and returns an empty route instead (`calculated_arrival_at: null`, `route_polyline: ""`, `steps: []`) as soon as the trip first comes within 100 m of its destination (same radius as the app's arrival prompt; stays off even if the user chooses to keep the trip going and drives away, since a route back to the same destination is useless), or once the trip has been running for more than 8 hours, as a fallback for trips that never reach it (counted from `started_at`, or from its first GPS point if that's unset). Guards against a trip that never gets finalized (dead battery, app killed, forgotten "Finalizar"): the app's 30s poll alone would exhaust the Routes free tier in under two days. The app keeps recording and showing live position; it just stops getting a suggested route and turn card, and the arrival time falls back to the original plan. `calculated_arrival_at` is now nullable in the response schema. Part of `api#76`. ([#77](https://github.com/TechVibe-Dev/trip-trace-api/pull/77))

## [0.10.0] - 29 Sep 2026

### Added

- `POST /trips/{id}/recalculate-eta` now also returns turn-by-turn steps (maneuver, instructions, distance) — same Google Routes call already made every 30s, no new cost. `steps[0]` is always "the next maneuver from here", since the route is computed from the trip's current position. Also now requests Spanish (`es-419`) instructions, which Google didn't default to. For `android#110`'s live navigation view. ([#70](https://github.com/TechVibe-Dev/trip-trace-api/pull/70))
- Rate-limited `POST /auth/login` (3/minute) and `POST /auth/register` (3/hour) using `slowapi`, keyed by client IP read from `X-Forwarded-For` (Render's standard uvicorn start command doesn't trust this header on its own, so `request.client.host` would otherwise resolve to Render's proxy for every caller, making the limit apply globally instead of per-IP). Mitigates brute-forcing a login password, and slows down both mass registration and using `/register`'s "already exists" response as an account-enumeration oracle — that oracle itself isn't fully closed by this (it still exists, just much slower to exploit); closing it outright would need email verification on registration, out of scope here. Exceeding a limit returns 429 with a `retry_after_seconds` field and a standard `Retry-After` header (a custom handler, not slowapi's own — that one only returns a plain-prose message) — for the frontend/Android to show a concrete "try again in N seconds" instead of a generic error. Counts live in-memory (no Redis or similar configured) — they reset on every restart/deploy, and would be tracked separately per worker if this ever ran with more than one; fine for today's single-instance setup, worth revisiting if that changes. From a security review of both this API and the Android app. ([#67](https://github.com/TechVibe-Dev/trip-trace-api/pull/67))

## [0.9.0] - 27 Sep 2026

### Added

- Added `favorite_places` — user-curated places (name + lat/lng), one list per user usable for a trip's origin, destination, or any stop. `POST /favorite-places`, `GET /favorite-places`, `DELETE /favorite-places/{id}`. Part of `android#81`. ([#63](https://github.com/TechVibe-Dev/trip-trace-api/pull/63))

### Changed

- Deploys to Render are now manual (`workflow_dispatch`, `.github/workflows/deploy.yml`) instead of automatic on every push to `main` — merging a release no longer immediately puts it live, giving a window to double-check or adjust something first. Can deploy any branch's current commit (via Render's deploy hook `ref` parameter), not just `main` — e.g. a release branch, to fix something in it before merging. Deploying anything other than `main` requires explicitly confirming (`confirm_non_main: 'yes'`), a guard against an accidental non-main deploy to production; deploying `main` itself needs no extra step. Requires disabling Render's own Auto-Deploy setting for this to take effect, and a `RENDER_DEPLOY_HOOK_URL` repo secret (both set up outside this repo, in Render's dashboard and GitHub's secret settings). ([#64](https://github.com/TechVibe-Dev/trip-trace-api/pull/64))

## [0.8.0] - 27 Sep 2026

### Added

- Added `PUT /auth/me/password` — deliberately separate from `PUT /auth/me` (which handles `username`), since changing a password is more security-sensitive than a plain profile edit. Requires `current_password`: the caller's JWT session proves they're logged in right now, not that they still know the password, so a stolen-but-valid token can't be used to lock the real owner out. Changing the password now also invalidates every existing token for that user, everywhere (frontend, Android, `/docs`) — new `users.password_changed_at` column, checked against each token's `iat` claim on every request, since stateless JWTs are never stored server-side and this is the only mechanism available to reject one before its own expiry. No per-device concept exists, so this is all-or-nothing by necessity — including the session that made the change itself. Part of `android#87`. ([#60](https://github.com/TechVibe-Dev/trip-trace-api/pull/60))

## [0.7.0] - 26 Sep 2026

### Changed

- `POST /auth/login` now accepts either the user's email or their username as the identifier — `username` already existed on the `User` model (used at registration), it just wasn't usable for login. Same either/or lookup `register()` already used to check for existing accounts. Closes `android#83`. ([#57](https://github.com/TechVibe-Dev/trip-trace-api/pull/57))

## [0.6.0] - 24 Sep 2026

### Added

- Added `POST /trips/{id}/recalculate-eta` — live ETA from the trip's latest recorded GPS point instead of its original origin, not persisted (keeps `calculated_arrival_at` meaning "the original plan"). Uploading GPS points now also checks for newly-reached stops within 100m, persisting `actual_arrival_at` on them. ([#54](https://github.com/TechVibe-Dev/trip-trace-api/pull/54))

## [0.5.3] - 23 Sep 2026

### Fixed

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

# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/), and this project adheres
to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.0] - 8 Sep 2026

### Added

- Initial FastAPI scaffold: config, database setup, JWT auth (register/login/me), SQLAlchemy models (User, Trip, Stop, GpsPoint).
- Set up Alembic migrations, with the initial migration creating `users`, `trips`, `stops`, `gps_points`. ([#13](https://github.com/TechVibe-Dev/trip-trace-api/pull/13))
- Extended JWT session length from 7 to 180 days. ([#11](https://github.com/TechVibe-Dev/trip-trace-api/pull/11))
- Finalized Trip and Stop schema: added `planned_departure_at`, `desired_arrival_at`, `calculated_arrival_at` to Trip, and split Stop's `arrival_at` into `planned_arrival_at`/`actual_arrival_at`. ([#10](https://github.com/TechVibe-Dev/trip-trace-api/pull/10))
- Automated backport PR creation (`main` → `develop`) after a release/hotfix merge. ([#9](https://github.com/TechVibe-Dev/trip-trace-api/pull/9))

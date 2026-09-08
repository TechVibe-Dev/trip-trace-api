# TripTrace API

Backend for TripTrace App: records car trips (actual route, planned route, stops) and
calculates trip metrics (max/min/average speed, slow and fast segments).

The main client is the Android app (Kotlin + Room), which records each trip locally and
syncs it with this API once it's finished.

## Stack

- FastAPI
- SQLAlchemy 2.0
- PostgreSQL
- JWT auth (python-jose + bcrypt)

## Local development

```bash
cp .env.default .env  # fill in DATABASE_URL and SECRET_KEY
pip install -r requirements.txt
./start_dev.sh
```

## Branching model

- `main`: released code only (production). Updated via a `release/{version}` branch merged with a PR.
- `develop`: integration branch. All `feature/{name}`, `doc/{name}`, etc. branches merge here via PR.
- `feature/{name}`, `doc/{name}`, ...: one branch per unit of work, branched off `develop`.
- `release/{version}` (e.g. `release/0.0.1`): cut from `develop` when preparing a production release; merged into `main` via PR.

See [CHANGELOG.md](./CHANGELOG.md) for release history.

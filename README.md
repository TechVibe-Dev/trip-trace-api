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

- `main`: released code only. Updated via PR from `develop`.
- `develop`: integration branch. All feature branches merge here.
- `feature/{name}`: one branch per unit of work, branched off `develop`.

## Releases

| Version | PR | Summary |
| --- | --- | --- |

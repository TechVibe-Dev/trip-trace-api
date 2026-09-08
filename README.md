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

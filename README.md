# TripTrace API

Backend de TripTrace App: registra viajes en auto (ruta real, ruta prevista, paradas) y calcula
metricas del viaje (velocidad maxima/minima/promedio, tramos lentos y rapidos).

El cliente principal es la app Android (Kotlin + Room), que graba cada viaje localmente y lo
sincroniza con esta API al finalizar.

## Stack

- FastAPI
- SQLAlchemy 2.0
- PostgreSQL
- JWT auth (python-jose + bcrypt)

## Desarrollo local

```bash
cp .env.default .env  # completar DATABASE_URL y SECRET_KEY
pip install -r requirements.txt
./start_dev.sh
```

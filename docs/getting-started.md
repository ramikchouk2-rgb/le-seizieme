# Documentation - Le Seizième

## Lancer le projet

### Prérequis

- Node.js 18+
- Python 3.10+
- PostgreSQL 14+ (optionnel pour le moment)

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Le frontend sera accessible sur `http://localhost:3000`.

### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate       # Windows
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Le backend sera accessible sur `http://localhost:8000`.

### Documentation API

La documentation interactive est disponible sur `http://localhost:8000/docs`.

## Architecture

Le projet est structuré en monorepo :

- `frontend/` : Application Next.js
- `backend/` : API FastAPI
- `database/` : Schémas SQL et migrations
- `docs/` : Documentation technique

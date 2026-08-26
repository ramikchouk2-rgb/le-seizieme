# Le Seizième

Plateforme professionnelle pour un traiteur événementiel.

## Architecture

```
le-seizieme/
├── frontend/          # Next.js + React + TypeScript + Tailwind CSS
├── backend/           # FastAPI + Python
├── database/          # Schémas SQL et migrations
├── deploy/            # Modèles de déploiement (NGINX, systemd)
├── docs/              # Documentation technique
├── scripts/           # Scripts de déploiement et vérification
├── backend/.env.example       # Variables d'environnement backend
├── frontend/.env.example      # Variables d'environnement frontend
└── README.md          # Ce fichier
```

## Stack technique

- **Frontend** : Next.js, React, TypeScript, Tailwind CSS
- **Backend** : Python, FastAPI
- **Base de données** : PostgreSQL

## Lancer le projet (développement local)

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Application disponible sur `http://localhost:3000`

### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate       # Windows
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

API disponible sur `http://localhost:8000`

### Base de données

```bash
# Créer la base de données PostgreSQL
createdb le_seizieme

# Appliquer le schéma
cd database
psql -U postgres -d le_seizieme -f schema.sql

# Insérer les données de référence
psql -U postgres -d le_seizieme -f seed.sql
```

## Variables d'environnement

### Backend

Copier `backend/.env.example` en `backend/.env` et remplir les valeurs.

### Frontend

Copier `frontend/.env.example` en `frontend/.env.local` et remplir les valeurs.

## Documentation de déploiement

Voir `DEPLOYMENT.md` pour les instructions de déploiement en production.

### Architecture recommandée (gratuite)

```
Frontend
   ↓
Render Free Web Service
   ↓
Render Free Backend Web Service
   ↓
Supabase Free PostgreSQL
```

Aucun VPS, SSH, NGINX ou domaine payant n'est requis.

# Production Deployment Guide — Le Seizième

## Current State

- Application code is production-ready
- All tests pass (135 backend, 44 E2E, 7/7 accessibility)
- Database schema is complete (21 tables, all enums, indexes, triggers)
- Deployment scripts and templates are prepared
- Actual deployment is blocked by missing production infrastructure

## Required Infrastructure

To deploy to production, the following must be provisioned:

- Linux VPS/cloud server with public IPv4 address
- Registered domain name with DNS management access
- SSH/sudo access to the production server
- Production PostgreSQL instance (can be on the same server)
- Firewall access (allow 22/SSH, 80/HTTP, 443/HTTPS; block 5432 from public)
- Ability to obtain TLS certificates (Let's Encrypt recommended)

**Note:** Development may continue on Windows, but production deployment scripts and configurations are intended for Linux. systemd, NGINX, and bash scripts require a Linux environment.

## Free Deployment — Render + Supabase

This is the **recommended** deployment method. It requires no VPS, no SSH, no NGINX, no systemd, and no paid infrastructure.

### Architecture

```
GitHub
  ↓
Render Free Web Services
  ├── Backend (FastAPI / Uvicorn)
  └── Frontend (Next.js)
  ↓
Supabase Free PostgreSQL
```

### What You Need

| Item | Cost | Notes |
|------|------|-------|
| Render account | Free | https://render.com |
| Supabase account | Free | https://supabase.com |
| GitHub repository | Free | Push this repo to GitHub |
| Domain | Free | Render provides `*.onrender.com` URLs |

### Step 1 — Prepare Supabase Database

1. Create a new Supabase project.
2. In the Supabase Dashboard, go to **SQL Editor**.
3. Enable the required PostgreSQL extensions:
   - `uuid-ossp`
   - `btree_gist`
4. Run `database/schema.sql` in the SQL Editor.
5. Run `database/seed.sql` in the SQL Editor.
6. Copy your Supabase connection string:
   - Settings → Database → Connection string → URI
   - Format: `postgresql://postgres:[PASSWORD]@[HOST]:[PORT]/postgres`

**Important:**
- Do NOT run `test-data.sql`, `event-test-data.sql`, or any other test SQL files.
- Supabase Free projects may pause after inactivity.
- Supabase Free does not expire after 30 days.

### Step 2 — Deploy Backend to Render

1. Push this repository to GitHub.
2. In Render Dashboard, click **New** → **Web Service**.
3. Connect your GitHub repository.
4. Configure the service:
   - **Name:** `le-seizieme-backend` (or your preferred name)
   - **Root Directory:** `backend`
   - **Environment:** `Python`
   - **Plan:** `Free`
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
5. Add environment variables:
   - `APP_ENV` = `production`
   - `DATABASE_URL` = your Supabase connection string
   - `JWT_SECRET_KEY` = a strong random secret (generate with `openssl rand -base64 48`)
   - `CORS_ORIGINS` = your frontend Render URL (e.g., `https://le-seizieme-frontend.onrender.com`)
   - `JWT_ALGORITHM` = `HS256`
   - `JWT_ACCESS_TOKEN_EXPIRE_MINUTES` = `60`
6. Click **Create Web Service**.

Render will automatically detect `backend/render.yaml` if present, or you can configure via the dashboard.

### Step 3 — Deploy Frontend to Render

1. In Render Dashboard, click **New** → **Web Service**.
2. Connect the same GitHub repository.
3. Configure the service:
   - **Name:** `le-seizieme-frontend` (or your preferred name)
   - **Root Directory:** `frontend`
   - **Environment:** `Node`
   - **Plan:** `Free`
   - **Build Command:** `npm install && npm run build`
   - **Start Command:** `npm start`
4. Add environment variables:
   - `NEXT_PUBLIC_API_URL` = your backend Render URL + `/api` (e.g., `https://le-seizieme-backend.onrender.com/api`)
   - `NEXT_PUBLIC_API_TIMEOUT_MS` = `15000`
5. Click **Create Web Service**.

### Step 4 — Configure CORS

After both services are deployed:

1. Update the backend `CORS_ORIGINS` to match the exact frontend Render URL.
2. Redeploy the backend if needed.

### Step 5 — Bootstrap Admin User

Use Render's **Shell** feature to run the admin bootstrap script:

```bash
cd backend
AUTH_INITIAL_ADMIN_EMAIL=admin@your-domain.com \
AUTH_INITIAL_ADMIN_PASSWORD=YourSecurePassword123! \
python scripts/init_admin.py
```

Or connect to Supabase and insert an admin user directly.

### Step 6 — Verify Deployment

1. Visit your frontend Render URL.
2. Test login with the admin account.
3. Verify API health: `https://<backend-url>/api/health`
4. Test a complete workflow (event creation, staff assignment, etc.).

### Render Free Limitations

- Free services spin down after 15 minutes of inactivity.
- The first request after sleeping can take 30–60 seconds.
- Free services cannot use custom domains with SSL without upgrading.
- Render Free PostgreSQL expires after 30 days — **do not use Render Postgres for this project**; use Supabase Free instead.

### Supabase Free Notes

- Supabase Free projects may pause after inactivity.
- Automatic backups are included.
- Use the Supabase SQL Editor for schema and seed data.
- Connection pooling may be required for high traffic; the default connection string is sufficient for this project.

---

## Prerequisites

- Python 3.10+
- Node.js 18+
- PostgreSQL 14+
- pip / npm
- NGINX or equivalent reverse proxy
- systemd or equivalent process supervisor
- TLS certificate (Let's Encrypt recommended)

---

## Backend

### Installation

```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### Environment Variables

Create a `.env` file in the `backend/` directory using `backend/.env.example` as a template:

```env
APP_ENV=production
DATABASE_URL=postgresql://USER:PASSWORD@HOST:PORT/DATABASE
JWT_SECRET_KEY=your-secure-jwt-secret-key-here
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=60
CORS_ORIGINS=https://your-production-frontend.com
AUTH_INITIAL_ADMIN_EMAIL=admin@your-domain.com
AUTH_INITIAL_ADMIN_PASSWORD=YourSecurePassword123!
```

**Required for production:**
- `APP_ENV=production` — Enables production validation
- `DATABASE_URL` — PostgreSQL connection string with non-default credentials
- `JWT_SECRET_KEY` — Secure random string for JWT signing
- `CORS_ORIGINS` — Production frontend origin(s), comma-separated

### Database

#### Fresh Installation

```bash
# Create the database
createdb le_seizieme

# Apply the complete schema
cd database
psql -U <production-user> -d le_seizieme -f schema.sql

# Insert reference data (cities, skills)
psql -U <production-user> -d le_seizieme -f seed.sql
```

#### Existing Database Upgrade

For databases initialized with an older version of `schema.sql`, apply migration files in order:

```bash
cd database/migrations
psql -U <production-user> -d le_seizieme -f 20240817_attendance.sql
psql -U <production-user> -d le_seizieme -f 20240818_authentication.sql
```

#### Bootstrap Admin User

```bash
cd backend
source venv/bin/activate
AUTH_INITIAL_ADMIN_EMAIL=admin@your-domain.com \
AUTH_INITIAL_ADMIN_PASSWORD=YourSecurePassword123! \
python scripts/init_admin.py
```

### Startup

```bash
cd backend
source venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

### systemd Service

A template is provided at `deploy/le-seizieme-backend.service.example`. Copy it to `/etc/systemd/system/le-seizieme-backend.service`, replacing `{{PROJECT_ROOT}}`, `{{USER}}`, and `{{GROUP}}` placeholders, then:

```bash
systemctl daemon-reload
systemctl enable le-seizieme-backend.service
systemctl restart le-seizieme-backend.service
```

### Health Check

```bash
curl http://localhost:8000/api/health
```

Expected response:
```json
{"status":"ok","project":"Le Seizième"}
```

---

## Frontend

### Installation

```bash
cd frontend
npm ci
```

### Environment Variables

Create a `.env.local` file in the `frontend/` directory using `frontend/.env.example` as a template:

```env
NEXT_PUBLIC_API_URL=https://your-api-domain.com/api
NEXT_PUBLIC_API_TIMEOUT_MS=15000
```

### Production Build

```bash
npm run build
```

### Production Start

```bash
npm start
```

Default port: 3000

### systemd Service

A template is provided at `deploy/le-seizieme-frontend.service.example`. Copy it to `/etc/systemd/system/le-seizieme-frontend.service`, replacing placeholders, then:

```bash
systemctl daemon-reload
systemctl enable le-seizieme-frontend.service
systemctl restart le-seizieme-frontend.service
```

---

## DNS Configuration

1. Create an A record pointing your domain to the production server's public IP address.
2. Create a CNAME record for `www` if needed.
3. Verify DNS propagation:
   ```bash
   dig your-domain.com
   ```
4. Ensure the domain resolves before proceeding with HTTPS setup.

---

## HTTPS Configuration

### Let's Encrypt Certificate

```bash
# Install certbot
sudo apt install certbot python3-certbot-nginx

# Obtain certificate
sudo certbot --nginx -d your-domain.com

# Test auto-renewal
sudo certbot renew --dry-run
```

### NGINX HTTPS Template

A template is provided at `deploy/nginx.conf.example`. Key requirements:
- Uncomment SSL certificate directives
- Replace `YOUR_DOMAIN` with the actual domain
- Ensure HTTP redirects to HTTPS
- Proxy `/api` to backend on port 8000
- Serve frontend on port 443

### Manual HTTPS (without certbot)

If not using certbot, place certificates at:
- `/etc/ssl/private/your-domain.com.key`
- `/etc/ssl/certs/your-domain.com.crt`

And configure NGINX with the SSL directives from the template.

---

## Firewall Requirements

Configure the production firewall to allow only necessary ports:

| Port | Protocol | Purpose | Source |
|------|----------|---------|--------|
| 22 | TCP | SSH | Admin IPs only |
| 80 | TCP | HTTP (redirect to HTTPS) | Any |
| 443 | TCP | HTTPS | Any |
| 5432 | TCP | PostgreSQL | Localhost only |

**Critical:** PostgreSQL (5432) must NOT be publicly exposed. The database should only accept connections from localhost or the application server's internal network.

### Example: ufw (Ubuntu)

```bash
sudo ufw allow 22/tcp
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw deny 5432/tcp
sudo ufw enable
```

### Example: firewalld (RHEL/CentOS)

```bash
sudo firewall-cmd --permanent --add-service=ssh
sudo firewall-cmd --permanent --add-service=http
sudo firewall-cmd --permanent --add-service=https
sudo firewall-cmd --reload
```

---

## Reverse Proxy Configuration

NGINX must proxy:
- `/` → Frontend Next.js on port 3000
- `/api` → Backend FastAPI on port 8000

Do not expose the backend directly to the internet.

The provided `deploy/nginx.conf.example` includes:
- HTTP to HTTPS redirect
- WebSocket support for Next.js
- Proxy headers for client IP and protocol
- Security headers
- Protection for sensitive files

---

## CORS Configuration

Production CORS must be explicitly set:

```env
CORS_ORIGINS=https://app.example.com,https://admin.example.com
```

Multiple origins are comma-separated. Wildcards (`*`) are not allowed.

The backend validates `CORS_ORIGINS` at startup and rejects default localhost values in production.

---

## Authentication

- JWT tokens stored in browser `localStorage`
- Token expiration: 60 minutes (configurable via `JWT_ACCESS_TOKEN_EXPIRE_MINUTES`)
- On 401: token cleared, user redirected to `/login`
- On 403: French error message "Accès refusé"

---

## Database Backup

### Initial Backup

After production database initialization:

```bash
pg_dump -U <production-user> -d le_seizieme > le_seizieme_backup_initial.sql
```

### Daily Backup Script

Create `/etc/cron.daily/le-seizieme-backup`:

```bash
#!/bin/bash
BACKUP_DIR="/var/backups/le-seizieme"
DATE=$(date +%Y%m%d_%H%M%S)
mkdir -p "$BACKUP_DIR"
pg_dump -U <production-user> -d le_seizieme | gzip > "$BACKUP_DIR/le_seizieme_$DATE.sql.gz"
find "$BACKUP_DIR" -name "le_seizieme_*.sql.gz" -mtime +30 -delete
```

Make it executable:
```bash
sudo chmod +x /etc/cron.daily/le-seizieme-backup
```

### Backup Retention

- Keep daily backups for 30 days
- Keep weekly backups for 3 months
- Keep monthly backups for 1 year

### Restore Procedure

```bash
# Stop backend service
sudo systemctl stop le-seizieme-backend.service

# Restore database
psql -U <production-user> -d le_seizieme < le_seizieme_backup_YYYYMMDD_HHMMSS.sql

# Start backend service
sudo systemctl start le-seizieme-backend.service
```

**Never test restoration on the production database.** Use a separate test database.

---

## Verification Checklist

1. Backend health endpoint returns 200
2. Frontend loads successfully over HTTPS
3. Login with valid credentials succeeds
4. Protected routes require authentication
5. Manager-only actions return 403 for STAFF
6. CORS preflight requests succeed from production origin
7. Event CRUD workflows function correctly
8. Transport recommendation returns valid response
9. Gamification endpoints return valid data
10. Database backup created successfully

---

## Production Verification Script

A verification script is provided at `scripts/verify_production.sh`. Usage:

```bash
sudo bash scripts/verify_production.sh https://app.example.com https://app.example.com/api
```

The script checks:
- Health endpoint
- Authentication
- Invalid credentials handling
- Frontend availability
- CORS headers

---

## Deployment Automation Scripts

Scripts are provided in the `scripts/` directory:

| Script | Purpose |
|--------|---------|
| `setup_production.sh` | Interactive production database and configuration setup |
| `deploy_backend.sh` | Backend deployment (venv, dependencies, systemd) |
| `deploy_frontend.sh` | Frontend deployment (npm ci, build, systemd) |
| `verify_production.sh` | Post-deployment verification |

**Important:** These scripts require manual review and customization before use. Never run them blindly in production.

---

## Notes

- No automated migration runner (e.g., Alembic) is configured. Schema changes are applied via raw SQL files in `database/migrations/`.
- JWT secret key must be rotated periodically in production
- Database credentials should use a dedicated application user with least-privilege access
- Production logs should be monitored for unhandled exceptions
- Always verify backups can be restored before relying on them

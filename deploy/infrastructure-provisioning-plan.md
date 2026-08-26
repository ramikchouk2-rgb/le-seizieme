# Infrastructure Provisioning Plan — Le Seizième

## Current Status

- **Codebase:** PRODUCTION READY
- **Tests:** 135 backend passed, 44 E2E passed, 7/7 accessibility, TypeScript clean, 13-route build PASS
- **Security:** PASS — no unresolved findings
- **Deployment artifacts:** Ready (scripts, systemd templates, NGINX template, documentation)
- **Infrastructure:** NOT AVAILABLE — awaiting production server provisioning

---

## 1. Target Architecture

```
                    INTERNET
                       │
                       ▼
                Public Domain
                       │
                     HTTPS
                       │
                       ▼
                    NGINX
                  Port 443
                       │
             ┌─────────┴─────────┐
             │                   │
             ▼                   ▼
        Frontend             /api
        Next.js 16             │
        Port 3000              ▼
                         FastAPI/Uvicorn
                           Port 8000
                               │
                               ▼
                          PostgreSQL
                           Port 5432
                         PRIVATE ONLY
```

### Components

| Component | Technology | Purpose |
|-----------|-----------|---------|
| OS | Ubuntu LTS | Production server OS |
| Reverse Proxy | NGINX | HTTPS termination, static file serving, API routing |
| Frontend | Next.js 16 | React application, server-side rendering |
| Backend | FastAPI + Uvicorn | REST API, business logic |
| Database | PostgreSQL 14+ | Data persistence |
| Process Supervisor | systemd | Service management, auto-restart |
| TLS | Let's Encrypt | HTTPS certificates |
| Firewall | UFW | Network access control |

### Key Design Principles

1. **PostgreSQL is NEVER publicly exposed** — Port 5432 accessible only from localhost or private network
2. **Backend and frontend are NOT directly exposed** — All traffic routes through NGINX
3. **HTTPS is mandatory** — HTTP redirects to HTTPS
4. **Separation of concerns** — Each component has a single, well-defined responsibility

---

## 2. Server Requirements

### Minimum Specifications

| Resource | Minimum | Rationale |
|----------|---------|-----------|
| vCPU | 2 | Sufficient for Uvicorn with 4 workers and NGINX |
| RAM | 4 GB | Handles Python runtime, Node.js, PostgreSQL buffer cache, and NGINX |
| Storage | 40 GB SSD | PostgreSQL data, application code, logs, backups |
| OS | Ubuntu 22.04 LTS or 24.04 LTS | Stable, well-supported, security updates |
| Network | Public IPv4 | Required for NGINX HTTPS and SSH access |
| Access | SSH + sudo | Required for deployment and maintenance |

### Recommended Specifications

| Resource | Recommended | Rationale |
|----------|-------------|-----------|
| vCPU | 4 | Headroom for concurrent event processing and report generation |
| RAM | 8 GB | Comfortable PostgreSQL buffer cache, faster queries |
| Storage | 80+ GB SSD | Room for database growth, backup retention, log accumulation |
| Backups | Automatic snapshots | Disaster recovery capability |
| Monitoring | Basic resource monitoring | Early detection of capacity issues |

### Why These Specifications Are Sufficient

**Current scale:** ~150 servers, multiple events, moderate concurrent usage.

**Backend:** FastAPI with Uvicorn (4 workers) is lightweight. Each worker handles one request at a time. 2 vCPU / 4 GB RAM is sufficient for the expected request volume.

**Frontend:** Next.js production server is memory-efficient. Static pages are pre-rendered. Dynamic pages are server-rendered on demand.

**PostgreSQL:** With proper indexes and the current data model, the database fits comfortably in memory. 4 GB RAM provides adequate buffer cache for the expected dataset.

**NGINX:** Minimal resource usage. Handles TLS termination and proxying efficiently.

**Headroom:** The minimum specs provide ~2x buffer for traffic spikes during event booking periods.

---

## 3. Domain Strategy

### Recommended Configuration

**Single domain approach:**

```text
YOUR_DOMAIN
```

with NGINX routing:

```text
/     → Frontend (Next.js on port 3000)
/api  → Backend (FastAPI on port 8000)
```

### Why Single Domain

1. **Simplifies CORS** — Only one origin to configure
2. **Simplifies NGINX** — One `server_name` directive
3. **Simplifies TLS** — One certificate covers all paths
4. **Matches existing architecture** — The prepared NGINX template already supports this
5. **No subdomain DNS required** — Reduces DNS management complexity

### Alternative (If Required)

If separate domains are preferred:

```text
app.YOUR_DOMAIN     → Frontend
api.YOUR_DOMAIN     → Backend
```

This requires:
- Additional DNS A/AAAA records
- Additional TLS certificates (or SAN certificate)
- Additional NGINX `server` blocks
- Updated `CORS_ORIGINS` with both domains

### DNS Records Required

| Type | Name | Value | Purpose |
|------|------|-------|---------|
| A | @ | VPS_PUBLIC_IP | Root domain |
| A | www | VPS_PUBLIC_IP | WWW subdomain (optional) |

### What to Provide

```text
YOUR_DOMAIN: example.com
YOUR_SERVER_IP: 203.0.113.10
```

---

## 4. Firewall Design

### Production Firewall Rules

| Port | Protocol | Source | Purpose | Action |
|------|----------|--------|---------|--------|
| 22 | TCP | Admin IPs only | SSH | ALLOW |
| 80 | TCP | Any | HTTP (redirect to HTTPS) | ALLOW |
| 443 | TCP | Any | HTTPS | ALLOW |
| 5432 | TCP | Localhost only | PostgreSQL | DENY (internet) |

### Implementation (UFW on Ubuntu)

```bash
# Reset to defaults
ufw default deny incoming
ufw default allow outgoing

# Allow SSH (restrict to admin IP after provisioning)
ufw allow 22/tcp

# Allow HTTP and HTTPS
ufw allow 80/tcp
ufw allow 443/tcp

# Block PostgreSQL from internet
ufw deny 5432/tcp

# Enable
ufw enable
```

### PostgreSQL Access Control

Even if the firewall allows localhost connections, PostgreSQL must also enforce host-based authentication:

```bash
# In pg_hba.conf:
local   all             le_seizieme_app                     scram-sha-256
host    all             le_seizieme_app    127.0.0.1/32     scram-sha-256
host    all             le_seizieme_app    ::1/128          scram-sha-256
```

### SSH Hardening (After Initial Setup)

```bash
# Disable root login
PermitRootLogin no

# Use key-based authentication only
PasswordAuthentication no

# Restrict to admin IPs (if static)
AllowUsers admin@trusted-ip
```

---

## 5. PostgreSQL Architecture

### Database Configuration

| Parameter | Value | Rationale |
|-----------|-------|-----------|
| DB_NAME | le_seizieme | Application database |
| DB_USER | le_seizieme_app | Dedicated application user (NOT postgres) |
| DB_OWNER | le_seizieme_app | Application user owns the schema |
| ENCODING | UTF8 | Unicode support |
| LC_COLLATE | fr_FR.UTF-8 | French locale sorting |
| LC_CTYPE | fr_FR.UTF-8 | French locale character classification |

### User Privileges

The `le_seizieme_app` user must have:
- `CREATE` on schema `public` (for initial setup)
- `USAGE` on all sequences
- `SELECT`, `INSERT`, `UPDATE`, `DELETE` on all tables
- Must NOT be a superuser
- Must NOT have `CREATEDB` or `CREATEROLE` privileges after setup

### Initialization Sequence

```bash
# 1. Create database user
createuser -U postgres -W le_seizieme_app

# 2. Create database
createdb -U postgres -O le_seizieme_app le_seizieme

# 3. Set locale-specific options
psql -U postgres -d le_seizieme -c "ALTER DATABASE le_seizieme SET lc_collate = 'fr_FR.UTF-8';"
psql -U postgres -d le_seizieme -c "ALTER DATABASE le_seizieme SET lc_ctype = 'fr_FR.UTF-8';"

# 4. Apply schema (as le_seizieme_app)
psql -U le_seizieme_app -d le_seizieme -f database/schema.sql

# 5. Apply seed data (as le_seizieme_app)
psql -U le_seizieme_app -d le_seizieme -f database/seed.sql

# 6. Verify
psql -U le_seizieme_app -d le_seizieme -c "\dt"
```

### What Must NEVER Be Applied to Production

```text
database/test-data.sql
database/event-test-data.sql
database/gamification-test-data.sql
database/urgent-event-test-data.sql
```

These contain fictional test servers, test events, and test assignments. They are for development and E2E testing only.

---

## 6. Production Environment Configuration

### Backend Environment (`backend/.env`)

```env
APP_ENV=production
DATABASE_URL=postgresql://le_seizieme_app:SECURE_PASSWORD@localhost:5432/le_seizieme
JWT_SECRET_KEY=GENERATE_WITH_openssl_rand_base64_48
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=60
CORS_ORIGINS=https://YOUR_DOMAIN
AUTH_INITIAL_ADMIN_EMAIL=admin@YOUR_DOMAIN
AUTH_INITIAL_ADMIN_PASSWORD=SET_SECURELY_ON_SERVER
```

### Frontend Environment (`frontend/.env.local`)

```env
NEXT_PUBLIC_API_URL=https://YOUR_DOMAIN/api
NEXT_PUBLIC_API_TIMEOUT_MS=15000
```

### Critical Rules

1. `APP_ENV` MUST be `production` — triggers security validation
2. `DATABASE_URL` MUST NOT contain `user:password` or `postgres:postgres`
3. `JWT_SECRET_KEY` MUST be set — 48+ random bytes via `openssl rand -base64 48`
4. `CORS_ORIGINS` MUST NOT contain `localhost` in production
5. `NEXT_PUBLIC_API_URL` MUST use `https://` in production
6. `NEXT_PUBLIC_API_URL` MUST exist BEFORE `npm run build` (Next.js embeds it at build time)

### What Must Never Be Committed

- `backend/.env`
- `frontend/.env.local`
- Actual production passwords
- Actual production JWT secrets
- Actual production database credentials

---

## 7. Deployment Sequence

### Phase A: Server Preparation

1. Provision VPS with Ubuntu LTS
2. Connect via SSH as root or sudo-capable user
3. Update OS packages: `apt update && apt upgrade -y`
4. Create deployment user (optional but recommended)
5. Configure SSH key authentication
6. Configure firewall (UFW): allow 22, 80, 443; deny 5432 from internet

### Phase B: Software Installation

7. Install Python 3.10+ and pip
8. Install Node.js 18+ and npm
9. Install PostgreSQL 14+
10. Install NGINX
11. Install Certbot
12. Install Git

### Phase C: Database Initialization

13. Create PostgreSQL database `le_seizieme`
14. Create dedicated user `le_seizieme_app` with strong password
15. Grant appropriate privileges
16. Apply `database/schema.sql`
17. Apply `database/seed.sql`
18. Verify 21 tables exist
19. Verify no test data exists
20. Verify indexes and constraints

### Phase D: Application Deployment

21. Clone repository to server
22. Backend: create venv, install dependencies
23. Backend: create `.env` with production values
24. Frontend: create `.env.local` with production values
25. Frontend: run `npm ci && npm run build`

### Phase E: Service Configuration

26. Install backend systemd service (`le-seizieme-backend.service`)
27. Install frontend systemd service (`le-seizieme-frontend.service`)
28. Enable and start both services
29. Verify backend responds on port 8000
30. Verify frontend responds on port 3000

### Phase F: NGINX Configuration

31. Copy `deploy/nginx.conf.example` to `/etc/nginx/sites-available/le-seizieme`
32. Replace `YOUR_DOMAIN` with actual domain
33. Uncomment SSL directives after certificate is obtained
34. Enable site: `ln -s /etc/nginx/sites-available/le-seizieme /etc/nginx/sites-enabled/`
35. Test configuration: `nginx -t`
36. Reload NGINX: `systemctl reload nginx`

### Phase G: DNS + HTTPS

37. Create DNS A record pointing domain to VPS IP
38. Wait for DNS propagation
39. Obtain Let's Encrypt certificate: `certbot --nginx -d YOUR_DOMAIN`
40. Verify HTTPS works
41. Verify HTTP redirects to HTTPS

### Phase H: Application Verification

42. Run admin bootstrap script
43. Verify `/api/health` returns 200
44. Verify frontend loads over HTTPS
45. Verify login with admin credentials
46. Verify CORS headers restrict to production origin
47. Verify protected routes redirect unauthenticated users
48. Verify STAFF receives 403 on manager-only endpoints

### Phase I: Business Workflow Verification

49. Create test event
50. Add requirements
51. Generate staff recommendations
52. Confirm staff assignments
53. Generate transport recommendation
54. Initialize attendance
55. Complete event
56. Create evaluation
57. Verify gamification data
58. Test urgent staffing
59. View report
60. Logout and verify redirect

### Phase J: Backup + Monitoring

61. Create initial `pg_dump` backup
62. Configure daily backup cron job
63. Configure log rotation
64. Verify backup restoration procedure on test database
65. Run final production verification script

---

## 8. Repository Artifact Verification

All deployment artifacts are present and verified:

| Artifact | Status | Key Verification |
|----------|--------|------------------|
| `backend/.env.example` | Present | Safe placeholders, no secrets |
| `frontend/.env.example` | Present | Safe placeholders, no secrets |
| `scripts/setup_production.sh` | Present | Only uses `schema.sql` + `seed.sql` |
| `scripts/deploy_backend.sh` | Present | Uses `python3`, checks dependencies |
| `scripts/deploy_frontend.sh` | Present | Checks Node.js/npm |
| `scripts/verify_production.sh` | Present | Enhanced with HTTPS check |
| `deploy/le-seizieme-backend.service.example` | Present | Includes `EnvironmentFile` |
| `deploy/le-seizieme-frontend.service.example` | Present | Includes `EnvironmentFile` |
| `deploy/nginx.conf.example` | Present | `/api` proxy preserves prefix |
| `DEPLOYMENT.md` | Present | Comprehensive with all procedures |
| `database/schema.sql` | Present | 21 tables, 14 enums, complete |
| `database/seed.sql` | Present | Reference data only |
| `backend/app/core/config.py` | Present | Production validation intact |
| `backend/requirements.txt` | Present | Unused deps removed |

---

## 9. Cost/Infrastructure Planning

### Cost Categories

| Category | Options | Notes |
|----------|---------|-------|
| VPS | DigitalOcean, Linode, Hetzner, OVH | ~5-15 EUR/month for minimum specs |
| Domain | Any registrar | ~10-15 EUR/year |
| PostgreSQL | Same VPS (free) or managed (~20-40 EUR/month) | Start with same VPS, migrate later if needed |
| Backups | VPS snapshots or S3-compatible storage | ~1-5 EUR/month |
| TLS | Let's Encrypt | Free |
| Monitoring | Self-hosted (Prometheus/Grafana) or SaaS | Optional for initial deployment |

### Recommended Approach

1. **Start simple:** Single VPS with PostgreSQL on the same machine
2. **Use Let's Encrypt:** Free TLS certificates
3. **Use VPS snapshots:** For backup and disaster recovery
4. **Upgrade later:** Separate database, CDN, monitoring as traffic grows

### What Is NOT Needed Initially

- Kubernetes or container orchestration
- Multiple availability zones
- Managed Kubernetes services
- Complex CI/CD pipelines
- Cloud-specific services (AWS RDS, etc.)
- CDN (until traffic justifies it)

---

## 10. Infrastructure Handoff

The following information must be provided to proceed with STEP 63 actual deployment:

```text
SERVER_PUBLIC_IP: <provided by infrastructure provider>
SSH_HOST: <same as SERVER_PUBLIC_IP or different hostname>
SSH_PORT: 22 (unless changed)
SSH_USER: <provided — must have sudo access>
DOMAIN: <registered domain name>
DNS_ACCESS: <DNS provider access or confirmation that records will be created>
POSTGRESQL_LOCATION: <same server / separate host / managed service>
ADMIN_EMAIL: <production administrator email>
```

### What Happens Next

Once the above information is provided, STEP 63 will:

1. Connect to the server via SSH
2. Execute the deployment sequence defined in Phase 7
3. Verify each step before proceeding
4. Produce a production deployment report with actual URLs and status

### What Will NOT Happen

- No passwords will be requested in the handoff
- No fake infrastructure will be created
- No local Windows machine will be exposed
- No development database will be used as production
- No test data will be imported

---

## 11. Deployment Readiness Gate

```text
STEP 62 COMPLETE

STATUS:
INFRASTRUCTURE PROVISIONING PLAN READY

CODEBASE:
PRODUCTION READY

DEPLOYMENT:
BLOCKED — WAITING FOR PRODUCTION SERVER

SECURITY:
PASS

TESTS:
135 backend passed
44 E2E passed
7/7 accessibility
TypeScript clean
13-route production build PASS

NEXT STEP:
STEP 63 — ACTUAL SERVER PROVISIONING AND DEPLOYMENT
```

### Minimum Required to Proceed

To move from STEP 62 to STEP 63, the following must be provided:

1. **VPS public IP address** or hostname
2. **SSH access** (host, port, username)
3. **Domain name** for the application
4. **PostgreSQL location** (same server or separate)
5. **Production admin email** for bootstrap

Once these are provided, actual deployment can begin immediately using the prepared scripts and templates.

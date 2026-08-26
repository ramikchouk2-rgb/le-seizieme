#!/usr/bin/env bash
set -euo pipefail

echo "=== Le Seizième - Production Setup ==="

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

if [ "$EUID" -ne 0 ]; then
    echo "ERROR: Production setup must be run as root."
    exit 1
fi

read -p "Production domain (e.g., app.example.com): " DOMAIN
if [ -z "$DOMAIN" ]; then
    echo "ERROR: Domain is required."
    exit 1
fi

read -p "Database host (default: localhost): " DB_HOST
DB_HOST=${DB_HOST:-localhost}

read -p "Database port (default: 5432): " DB_PORT
DB_PORT=${DB_PORT:-5432}

read -p "Database name (default: le_seizieme): " DB_NAME
DB_NAME=${DB_NAME:-le_seizieme}

read -p "Database user: " DB_USER
if [ -z "$DB_USER" ]; then
    echo "ERROR: Database user is required."
    exit 1
fi

read -sp "Database password: " DB_PASSWORD
echo
if [ -z "$DB_PASSWORD" ]; then
    echo "ERROR: Database password is required."
    exit 1
fi

read -p "Admin email: " ADMIN_EMAIL
if [ -z "$ADMIN_EMAIL" ]; then
    echo "ERROR: Admin email is required."
    exit 1
fi

read -sp "Admin password: " ADMIN_PASSWORD
echo
if [ -z "$ADMIN_PASSWORD" ]; then
    echo "ERROR: Admin password is required."
    exit 1
fi

JWT_SECRET=$(openssl rand -base64 48)
if [ -z "$JWT_SECRET" ]; then
    echo "ERROR: Failed to generate JWT secret."
    exit 1
fi

echo ""
echo "=== Configuration Summary ==="
echo "Domain: $DOMAIN"
echo "Database: $DB_USER@$DB_HOST:$DB_PORT/$DB_NAME"
echo "Admin: $ADMIN_EMAIL"
echo ""

read -p "Proceed with setup? (yes/no): " CONFIRM
if [ "$CONFIRM" != "yes" ]; then
    echo "Setup cancelled."
    exit 0
fi

echo "Creating database user..."
su - postgres -c "psql -c \"CREATE USER $DB_USER WITH PASSWORD '$DB_PASSWORD';\"" || true

echo "Creating database..."
su - postgres -c "psql -c \"CREATE DATABASE $DB_NAME OWNER $DB_USER;\"" || true

echo "Granting privileges..."
su - postgres -c "psql -d $DB_NAME -c \"GRANT ALL ON SCHEMA public TO $DB_USER;\""

echo "Applying schema..."
cd "$PROJECT_ROOT/database"
su - postgres -c "psql -U $DB_USER -d $DB_NAME -f schema.sql"

echo "Applying seed data..."
su - postgres -c "psql -U $DB_USER -d $DB_NAME -f seed.sql"

echo "Configuring backend..."
cat > "$PROJECT_ROOT/backend/.env" <<EOF
APP_ENV=production
DATABASE_URL=postgresql://$DB_USER:$DB_PASSWORD@$DB_HOST:$DB_PORT/$DB_NAME
JWT_SECRET_KEY=$JWT_SECRET
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=60
CORS_ORIGINS=https://$DOMAIN
AUTH_INITIAL_ADMIN_EMAIL=$ADMIN_EMAIL
AUTH_INITIAL_ADMIN_PASSWORD=$ADMIN_PASSWORD
EOF

echo "Configuring frontend..."
cat > "$PROJECT_ROOT/frontend/.env.local" <<EOF
NEXT_PUBLIC_API_URL=https://$DOMAIN/api
NEXT_PUBLIC_API_TIMEOUT_MS=15000
EOF

echo "Bootstrapping admin user..."
cd "$PROJECT_ROOT/backend"
source venv/bin/activate
AUTH_INITIAL_ADMIN_EMAIL="$ADMIN_EMAIL" \
AUTH_INITIAL_ADMIN_PASSWORD="$ADMIN_PASSWORD" \
python scripts/init_admin.py

echo "Creating backup..."
cd "$PROJECT_ROOT"
BACKUP_FILE="le_seizieme_backup_$(date +%Y%m%d_%H%M%S).sql"
su - postgres -c "pg_dump -U $DB_USER -d $DB_NAME" > "$BACKUP_FILE"
echo "Backup created: $BACKUP_FILE"

echo ""
echo "=== Setup Complete ==="
echo "Next steps:"
echo "1. Configure NGINX with $DEPLOY_DIR/nginx.conf.example"
echo "2. Install SSL certificate for $DOMAIN"
echo "3. Run $SCRIPT_DIR/deploy_backend.sh"
echo "4. Run $SCRIPT_DIR/deploy_frontend.sh"
echo "5. Verify with $SCRIPT_DIR/verify_production.sh"

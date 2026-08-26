#!/usr/bin/env bash
set -euo pipefail

echo "=== Le Seizième - Backend Deployment ==="

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
BACKEND_DIR="$PROJECT_ROOT/backend"
DEPLOY_DIR="$PROJECT_ROOT/deploy"

if [ ! -f "$BACKEND_DIR/.env" ]; then
    echo "ERROR: backend/.env not found. Copy backend/.env.example to backend/.env and configure it."
    exit 1
fi

if ! command -v python3 &> /dev/null; then
    echo "ERROR: python3 is not installed or not in PATH."
    exit 1
fi

echo "Installing backend dependencies..."
cd "$BACKEND_DIR"
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

echo "Verifying production configuration..."
python3 -c "from app.core.config import settings; settings.validate_production()"

echo "Creating systemd service file..."
sed -e "s|{{PROJECT_ROOT}}|$PROJECT_ROOT|g" \
    -e "s|{{USER}}|$(whoami)|g" \
    -e "s|{{GROUP}}|$(id -gn)|g" \
    "$DEPLOY_DIR/le-seizieme-backend.service.example" \
    > /etc/systemd/system/le-seizieme-backend.service

echo "Reloading systemd..."
systemctl daemon-reload

echo "Enabling backend service..."
systemctl enable le-seizieme-backend.service
systemctl restart le-seizieme-backend.service

echo "Backend deployed successfully."

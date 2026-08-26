#!/usr/bin/env bash
set -euo pipefail

echo "=== Le Seizième - Frontend Deployment ==="

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
FRONTEND_DIR="$PROJECT_ROOT/frontend"
DEPLOY_DIR="$PROJECT_ROOT/deploy"

if [ ! -f "$FRONTEND_DIR/.env.local" ]; then
    echo "ERROR: frontend/.env.local not found. Copy frontend/.env.example to frontend/.env.local and configure it."
    exit 1
fi

if ! command -v node &> /dev/null; then
    echo "ERROR: Node.js is not installed or not in PATH."
    exit 1
fi

if ! command -v npm &> /dev/null; then
    echo "ERROR: npm is not installed or not in PATH."
    exit 1
fi

echo "Installing frontend dependencies..."
cd "$FRONTEND_DIR"
npm ci

echo "Building frontend..."
npm run build

echo "Creating systemd service file..."
sed -e "s|{{PROJECT_ROOT}}|$PROJECT_ROOT|g" \
    -e "s|{{USER}}|$(whoami)|g" \
    -e "s|{{GROUP}}|$(id -gn)|g" \
    "$DEPLOY_DIR/le-seizieme-frontend.service.example" \
    > /etc/systemd/system/le-seizieme-frontend.service

echo "Reloading systemd..."
systemctl daemon-reload

echo "Enabling frontend service..."
systemctl enable le-seizieme-frontend.service
systemctl restart le-seizieme-frontend.service

echo "Frontend deployed successfully."

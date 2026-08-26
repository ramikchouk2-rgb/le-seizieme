#!/usr/bin/env bash
set -euo pipefail

echo "=== Le Seizième - Production Verification ==="

FRONTEND_URL="${1:-http://localhost:3000}"
API_URL="${2:-http://localhost:8000/api}"

FAILED=0

check() {
    local name="$1"
    local result="$2"
    if [ "$result" -eq 0 ]; then
        echo "PASS: $name"
    else
        echo "FAIL: $name"
        FAILED=$((FAILED + 1))
    fi
}

echo "Target frontend: $FRONTEND_URL"
echo "Target API:      $API_URL"
echo ""

# Health check
echo "Checking health endpoint..."
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "$API_URL/health")
if [ "$HTTP_CODE" = "200" ]; then
    check "Health endpoint returns 200" 0
else
    check "Health endpoint returns 200 (got $HTTP_CODE)" 1
fi

# Authentication endpoint reachability
echo "Checking authentication endpoint..."
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$API_URL/auth/login" \
    -H "Content-Type: application/json" \
    -d '{"email":"test@example.com","password":"test"}')
if [ "$HTTP_CODE" = "401" ] || [ "$HTTP_CODE" = "422" ]; then
    check "Auth endpoint rejects invalid credentials" 0
else
    check "Auth endpoint rejects invalid credentials (got $HTTP_CODE)" 1
fi

# Frontend
echo "Checking frontend..."
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "$FRONTEND_URL")
if [ "$HTTP_CODE" = "200" ]; then
    check "Frontend loads" 0
else
    check "Frontend loads (got $HTTP_CODE)" 1
fi

# CORS check
echo "Checking CORS..."
CORS=$(curl -s -I -X OPTIONS "$API_URL/health" \
    -H "Origin: $FRONTEND_URL" \
    -H "Access-Control-Request-Method: GET" \
    -H "Access-Control-Request-Headers: authorization" | grep -i "access-control-allow-origin" || true)
if [ -n "$CORS" ]; then
    check "CORS headers present" 0
else
    check "CORS headers present" 1
fi

# HTTPS check
if [[ "$FRONTEND_URL" == https://* ]]; then
    echo "Checking HTTPS..."
    SSL_RESULT=$(echo | openssl s_client -connect "${FRONTEND_URL#https://}:443" -servername "${FRONTEND_URL#https://}" 2>/dev/null | grep -i "verify return:1" || true)
    if [ -n "$SSL_RESULT" ]; then
        check "HTTPS certificate valid" 0
    else
        check "HTTPS certificate valid" 1
    fi
else
    echo "SKIP: HTTPS check (frontend URL is not HTTPS)"
fi

echo ""
if [ "$FAILED" -eq 0 ]; then
    echo "All verification checks passed."
    exit 0
else
    echo "$FAILED check(s) failed."
    exit 1
fi

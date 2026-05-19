#!/bin/sh
set -e

# Set default backend URLs for Render (fallback to localhost for local dev)
export AUTH_SERVICE_URL="${AUTH_SERVICE_URL:-http://auth-service:10000}"
export INVENTORY_SERVICE_URL="${INVENTORY_SERVICE_URL:-http://inventory-service:10000}"
export TRANSACTION_SERVICE_URL="${TRANSACTION_SERVICE_URL:-http://transaction-service:10000}"
export AGENTIC_SERVICE_URL="${AGENTIC_SERVICE_URL:-http://agentic-service:10000}"

# Start nginx
exec nginx -g "daemon off;"

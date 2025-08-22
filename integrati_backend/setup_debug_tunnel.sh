#!/bin/sh
set -euo pipefail

echo "[debug-tunnel] Setting up Cloudflare tunnel and Pub/Sub for debug mode..."

APP_PORT="8000"
CLOUDFLARED_BIN="/app/cloudflared"
GCP_PROJECT_ID="${GCP_PROJECT_ID:-}"
PUBSUB_TOPIC_NAME="${PUBSUB_TOPIC_NAME:-gmail-push-topic}"
PUBSUB_SUB_NAME="${PUBSUB_SUB_NAME:-gmail-push-sub}"
GOOGLE_KEY_PATH="/app/integrati-app-pubsub-loginkey.json"

if [ ! -f "$GOOGLE_KEY_PATH" ]; then
  echo "[debug-tunnel] ERROR: Google service account key not found at $GOOGLE_KEY_PATH" >&2
  exit 1
fi

# Download cloudflared if not present
if [ ! -x "$CLOUDFLARED_BIN" ]; then
  echo "[debug-tunnel] Downloading cloudflared..."
  ARCH=$(uname -m)
  case "$ARCH" in
    x86_64|amd64) CFLARE_URL="https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64" ;;
    aarch64|arm64) CFLARE_URL="https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-arm64" ;;
    *) echo "[debug-tunnel] Unsupported arch: $ARCH" >&2; exit 1 ;;
  esac
  curl -fsSL "$CFLARE_URL" -o "$CLOUDFLARED_BIN"
  chmod +x "$CLOUDFLARED_BIN"
fi

echo "[debug-tunnel] Starting Cloudflare tunnel for port $APP_PORT..."
"$CLOUDFLARED_BIN" tunnel --url "http://localhost:$APP_PORT" > /tmp/cloudflared.log 2>&1 &
CFLARE_PID=$!

# Wait for tunnel URL to appear
PUBLIC_URL=""
for i in $(seq 1 60); do
  if grep -Eo "https://[a-zA-Z0-9.-]+\\.trycloudflare\\.com" /tmp/cloudflared.log >/tmp/cf_url.txt 2>/dev/null; then
    PUBLIC_URL=$(tail -n1 /tmp/cf_url.txt)
    if [ -n "$PUBLIC_URL" ]; then
      break
    fi
  fi
  sleep 1
done

if [ -z "$PUBLIC_URL" ]; then
  echo "[debug-tunnel] ERROR: Failed to obtain Cloudflare public URL" >&2
  echo "==== cloudflared log ===="
  tail -n 200 /tmp/cloudflared.log || true
  exit 1
fi

echo "[debug-tunnel] Cloudflare public URL: $PUBLIC_URL"

# Export env vars for app
export WEBHOOK_PUBLIC_BASE_URL="$PUBLIC_URL"

if [ -z "$GCP_PROJECT_ID" ]; then
  echo "[debug-tunnel] GCP_PROJECT_ID not set; attempting to read from service account key..."
  GCP_PROJECT_ID=$(python - <<'PY'
import json,sys
try:
    with open('/app/integrati-app-pubsub-loginkey.json','r') as f:
        print(json.load(f).get('project_id',''))
except Exception as e:
    print('', end='')
PY
)
fi

if [ -z "$GCP_PROJECT_ID" ]; then
  echo "[debug-tunnel] ERROR: Could not determine GCP_PROJECT_ID (env missing and key had no project_id)" >&2
  exit 1
fi
echo "[debug-tunnel] Using GCP project: $GCP_PROJECT_ID"

echo "[debug-tunnel] Authenticating to gcloud with service account..."
gcloud auth activate-service-account --key-file="$GOOGLE_KEY_PATH"
gcloud config set project "$GCP_PROJECT_ID"

echo "[debug-tunnel] Ensuring Pub/Sub API enabled..."
gcloud services enable pubsub.googleapis.com || true

TOPIC_FULL="projects/$GCP_PROJECT_ID/topics/$PUBSUB_TOPIC_NAME"

echo "[debug-tunnel] Creating topic $TOPIC_FULL (if missing)..."
gcloud pubsub topics describe "$TOPIC_FULL" >/dev/null 2>&1 || gcloud pubsub topics create "$PUBSUB_TOPIC_NAME"

echo "[debug-tunnel] Granting Gmail publisher to topic (non-fatal if lacking permission)..."
if ! gcloud pubsub topics add-iam-policy-binding "$TOPIC_FULL" \
  --member='serviceAccount:gmail-api-push@system.gserviceaccount.com' \
  --role='roles/pubsub.publisher'; then
  echo "[debug-tunnel] WARNING: Failed to grant gmail-api-push@system.gserviceaccount.com publisher on $TOPIC_FULL.\nGmail push may not deliver until this binding is added by a project owner. Continuing..." >&2
fi

SUB_NAME="$PUBSUB_SUB_NAME"
echo "[debug-tunnel] Creating push subscription $SUB_NAME (if missing)..."
if ! gcloud pubsub subscriptions describe "$SUB_NAME" >/dev/null 2>&1; then
  gcloud pubsub subscriptions create "$SUB_NAME" \
    --topic="$TOPIC_FULL" \
    --push-endpoint="$PUBLIC_URL/webhooks/google/gmail"
else
  # Ensure push endpoint matches current tunnel URL on every startup
  gcloud pubsub subscriptions update "$SUB_NAME" \
    --push-endpoint="$PUBLIC_URL/webhooks/google/gmail" || true
fi

# Export topic for app
export GMAIL_PUBSUB_TOPIC="$TOPIC_FULL"

echo "[debug-tunnel] Setup complete! Tunnel and Pub/Sub configured."
echo "[debug-tunnel] Cloudflare URL: $PUBLIC_URL"
echo "[debug-tunnel] Pub/Sub Topic: $GMAIL_PUBSUB_TOPIC"
echo "[debug-tunnel] Keeping tunnel alive for debug mode..."

# Keep the script running to maintain the tunnel
while true; do sleep 3600; done

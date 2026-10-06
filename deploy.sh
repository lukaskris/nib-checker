#!/usr/bin/env bash
# Deploy nib-checker to the app server and restart the service.
# Usage: SSH_HOST=host SSH_USER=user SSHPASS=pass REMOTE_DIR=/srv/nib-checker ./deploy.sh
set -euo pipefail

SSH_HOST="${SSH_HOST:?SSH_HOST not set}"
SSH_USER="${SSH_USER:?SSH_USER not set}"
REMOTE_DIR="${REMOTE_DIR:?REMOTE_DIR not set}"
SERVICE="${SERVICE:-nib-checker}"
URL="${URL:-http://${SSH_HOST}:8020}"
SSH_CMD="sshpass -e ssh -o StrictHostKeyChecking=no"

if ! command -v sshpass >/dev/null; then
  echo "sshpass required: brew install sshpass (or hudochenkov/sshpass)" >&2
  exit 1
fi
if [[ -z "${SSHPASS:-}" ]]; then
  echo "SSHPASS env var not set" >&2
  exit 1
fi

echo ">> rsync -> ${SSH_USER}@${SSH_HOST}:${REMOTE_DIR}"
rsync -az --delete \
  --exclude '.venv' --exclude '.cache' --exclude '__pycache__' \
  --exclude '.git' --exclude 'node_modules' --exclude '.DS_Store' \
  -e "$SSH_CMD" \
  ./ "${SSH_USER}@${SSH_HOST}:${REMOTE_DIR}/"

echo ">> sync deps + restart ${SERVICE}"
$SSH_CMD "${SSH_USER}@${SSH_HOST}" "
  cd ${REMOTE_DIR}
  export PATH=\"/root/.local/bin:\$PATH\"
  uv sync --quiet
  systemctl restart ${SERVICE}
"

echo ">> health check"
for i in $(seq 1 15); do
  code=$(curl -s -o /dev/null -w '%{http_code}' --max-time 5 "$URL" || true)
  if [[ "$code" == "200" ]]; then
    echo "deployed: $URL"
    exit 0
  fi
  sleep 2
done
echo "service did not come up: $URL (check: ssh ${SSH_USER}@${SSH_HOST} journalctl -u ${SERVICE} -n 30)" >&2
exit 1

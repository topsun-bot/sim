#!/usr/bin/env bash
# Isaac profile 冒烟测试：MCAP inspect + Omniverse 运行时检测
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"
ENV_FILE="${ENV_FILE:-$SCRIPT_DIR/.env}"

cd "$ROOT_DIR"

echo "==> [1/2] Isaac inspect MCAP"
COMPOSE_PROFILES=isaac docker compose --env-file "$ENV_FILE" run --rm replay-isaac \
  inspect /data/eda9cc2192f7.mcap

echo "==> [2/2] Isaac Omniverse 运行时检测"
COMPOSE_PROFILES=isaac docker compose --env-file "$ENV_FILE" run --rm \
  --entrypoint /isaac-sim/python.sh replay-isaac \
  -c "import omni; import replay; from replay.backends.isaac_backend import IsaacSimBackend; b=IsaacSimBackend(); assert b._available; print('omni OK')"

echo "Isaac profile 冒烟测试通过。"

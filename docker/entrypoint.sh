#!/usr/bin/env bash
set -euo pipefail

# Isaac Sim 5.1：加载 Omniverse Python 环境（omni 模块依赖此配置）
if [[ -f /isaac-sim/setup_python_env.sh ]]; then
  export PYTHONPATH="${PYTHONPATH:-}"
  export LD_LIBRARY_PATH="${LD_LIBRARY_PATH:-}"
  # shellcheck disable=SC1091
  source /isaac-sim/setup_python_env.sh
fi

_backend="${REPLAY_BACKEND:-mujoco}"
if [[ "$_backend" == "isaac" || "$_backend" == "both" ]]; then
  : "${NVIDIA_VISIBLE_DEVICES:?NVIDIA_VISIBLE_DEVICES required for Isaac Sim}"
  : "${ACCEPT_EULA:?ACCEPT_EULA=Y required for Isaac Sim NGC container}"
fi

if [[ "${REPLAY_BACKEND:-}" == "mujoco" || -z "${REPLAY_BACKEND:-}" ]]; then
  : "${MUJOCO_GL:=egl}"
fi

REPLAY_BIN="replay"
if [[ -x /isaac-sim/kit/python/bin/replay ]]; then
  REPLAY_BIN="/isaac-sim/kit/python/bin/replay"
fi

exec "$REPLAY_BIN" "$@"

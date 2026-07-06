#!/usr/bin/env bash
# 校验 sim-replay Docker 环境变量；通过时 export 供 compose / setup 使用。
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="${ENV_FILE:-$SCRIPT_DIR/.env}"

if [[ ! -f "$ENV_FILE" ]]; then
  echo "错误: 未找到 $ENV_FILE，请先运行 docker/setup.sh 或复制 docker/env.example" >&2
  exit 1
fi

# shellcheck disable=SC1090
set -a
source "$ENV_FILE"
set +a

REPLAY_BACKEND="${REPLAY_BACKEND:-mujoco}"
MUJOCO_GL="${MUJOCO_GL:-egl}"
IMAGE_MUJOCO="${IMAGE_MUJOCO:-sim-replay:mujoco}"
IMAGE_ISAAC="${IMAGE_ISAAC:-sim-replay:isaac}"
NVIDIA_VISIBLE_DEVICES="${NVIDIA_VISIBLE_DEVICES:-all}"
NVIDIA_DRIVER_CAPABILITIES="${NVIDIA_DRIVER_CAPABILITIES:-compute,utility,graphics}"

ERRORS=0
warn() { echo "  [警告] $*" >&2; }
fail() { echo "  [失败] $*" >&2; ERRORS=$((ERRORS + 1)); }
ok()   { echo "  [通过] $*"; }

echo "==> 校验 Docker 环境 ($ENV_FILE)"
echo "    目标后端: $REPLAY_BACKEND"

# Docker daemon
if ! docker info >/dev/null 2>&1; then
  fail "Docker daemon 未运行或无权限访问"
else
  ok "Docker daemon 可用"
fi

# 数据目录
DATA_DIR="${REPLAY_DATA_DIR:-./data}"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"
DATA_ABS="$ROOT_DIR/${DATA_DIR#./}"
if [[ ! -f "$DATA_ABS/eda9cc2192f7.mcap" ]]; then
  fail "示例 MCAP 不存在: $DATA_ABS/eda9cc2192f7.mcap"
else
  ok "示例数据: $DATA_ABS/eda9cc2192f7.mcap"
fi

validate_mujoco() {
  echo "-- MuJoCo --"
  case "$MUJOCO_GL" in
    egl|osmesa|glfw) ok "MUJOCO_GL=$MUJOCO_GL" ;;
    *) fail "MUJOCO_GL 无效: $MUJOCO_GL（允许: egl, osmesa, glfw）" ;;
  esac
  if [[ "$MUJOCO_GL" == "egl" ]]; then
    if command -v nvidia-smi >/dev/null 2>&1; then
      ok "NVIDIA GPU 可用（EGL 渲染）"
    else
      warn "未检测到 nvidia-smi，EGL 可能失败，可改用 MUJOCO_GL=osmesa"
    fi
  fi
  if [[ -z "${IMAGE_MUJOCO:-}" ]]; then
    fail "IMAGE_MUJOCO 未设置"
  else
    ok "镜像标签: $IMAGE_MUJOCO"
  fi
}

validate_isaac() {
  echo "-- Isaac Sim --"
  if [[ -z "${IMAGE_ISAAC:-}" ]]; then
    fail "IMAGE_ISAAC 未设置"
  else
    ok "镜像标签: $IMAGE_ISAAC"
  fi

  if [[ -z "${NVIDIA_VISIBLE_DEVICES:-}" ]]; then
    fail "NVIDIA_VISIBLE_DEVICES 未设置"
  else
    ok "NVIDIA_VISIBLE_DEVICES=$NVIDIA_VISIBLE_DEVICES"
  fi

  if [[ -z "${NVIDIA_DRIVER_CAPABILITIES:-}" ]]; then
    fail "NVIDIA_DRIVER_CAPABILITIES 未设置"
  else
    ok "NVIDIA_DRIVER_CAPABILITIES=$NVIDIA_DRIVER_CAPABILITIES"
  fi

  if command -v nvidia-smi >/dev/null 2>&1; then
    ok "NVIDIA 驱动: $(nvidia-smi --query-gpu=driver_version --format=csv,noheader | head -1)"
  else
    fail "未检测到 NVIDIA 驱动（Isaac Sim 需要 GPU）"
  fi

  if [[ -n "${ISAAC_SIM_PATH:-}" ]]; then
    if [[ -d "$ISAAC_SIM_PATH" ]]; then
      ok "ISAAC_SIM_PATH=$ISAAC_SIM_PATH"
    else
      fail "ISAAC_SIM_PATH 不存在: $ISAAC_SIM_PATH"
    fi
  else
    warn "ISAAC_SIM_PATH 未设置（使用 stub 后端，完整 Omniverse 需挂载安装目录）"
  fi

  if [[ -n "${NGC_API_KEY:-}" ]]; then
    ok "NGC_API_KEY 已配置"
  elif [[ -n "${ISAAC_SIM_IMAGE:-}" ]] && [[ "$ISAAC_SIM_IMAGE" == nvcr.io/* ]]; then
    warn "NGC_API_KEY 未设置，拉取 $ISAAC_SIM_IMAGE 可能失败"
  fi
}

case "$REPLAY_BACKEND" in
  mujoco) validate_mujoco ;;
  isaac)  validate_isaac ;;
  both)   validate_mujoco; validate_isaac ;;
  *)      fail "REPLAY_BACKEND 无效: $REPLAY_BACKEND（允许: mujoco, isaac, both）" ;;
esac

echo ""
if [[ $ERRORS -gt 0 ]]; then
  echo "环境校验失败（$ERRORS 项），请修正 $ENV_FILE 后重试。" >&2
  exit 1
fi

echo "环境校验全部通过。"
export ENV_FILE REPLAY_BACKEND MUJOCO_GL IMAGE_MUJOCO IMAGE_ISAAC
export NVIDIA_VISIBLE_DEVICES NVIDIA_DRIVER_CAPABILITIES ISAAC_SIM_PATH ISAAC_SIM_IMAGE

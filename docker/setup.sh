#!/usr/bin/env bash
# 校验环境变量 → 保存配置 → 构建镜像 → 导出 tar
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"
ENV_FILE="$SCRIPT_DIR/.env"
CONFIG_DIR="$SCRIPT_DIR/config"
EXPORT_DIR="${IMAGE_EXPORT_DIR:-$SCRIPT_DIR/images}"

BUILD_MUJOCO=0
BUILD_ISAAC=0
SKIP_EXPORT=0
SKIP_RUN=0

usage() {
  cat <<'EOF'
用法: docker/setup.sh [选项]

  --backend mujoco|isaac|both   覆盖 REPLAY_BACKEND（默认读取 .env）
  --no-export                   跳过 docker save 导出镜像
  --no-run                      构建后不运行 inspect 冒烟测试
  -h, --help                    显示帮助

流程:
  1. 从 env.example 生成 .env（若不存在）
  2. validate_env.sh 校验环境变量
  3. 保存配置快照到 docker/config/
  4. docker compose build
  5. docker save 导出到 docker/images/
  6. MuJoCo inspect 冒烟测试
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --backend)
      REPLAY_BACKEND_OVERRIDE="$2"
      shift 2
      ;;
    --no-export) SKIP_EXPORT=1; shift ;;
    --no-run)    SKIP_RUN=1; shift ;;
    -h|--help)   usage; exit 0 ;;
    *) echo "未知参数: $1" >&2; usage; exit 1 ;;
  esac
done

# 初始化 .env
if [[ ! -f "$ENV_FILE" ]]; then
  echo "==> 从 env.example 创建 $ENV_FILE"
  cp "$SCRIPT_DIR/env.example" "$ENV_FILE"
fi

if [[ -n "${REPLAY_BACKEND_OVERRIDE:-}" ]]; then
  if grep -q '^REPLAY_BACKEND=' "$ENV_FILE"; then
    sed -i "s/^REPLAY_BACKEND=.*/REPLAY_BACKEND=${REPLAY_BACKEND_OVERRIDE}/" "$ENV_FILE"
  else
    echo "REPLAY_BACKEND=${REPLAY_BACKEND_OVERRIDE}" >> "$ENV_FILE"
  fi
fi

# 校验
echo "==> 校验环境变量"
ENV_FILE="$ENV_FILE" bash "$SCRIPT_DIR/validate_env.sh"

# shellcheck disable=SC1090
set -a
source "$ENV_FILE"
set +a

REPLAY_BACKEND="${REPLAY_BACKEND:-mujoco}"

case "$REPLAY_BACKEND" in
  mujoco) BUILD_MUJOCO=1 ;;
  isaac)  BUILD_ISAAC=1 ;;
  both)   BUILD_MUJOCO=1; BUILD_ISAAC=1 ;;
esac

# 保存配置快照
STAMP="$(date +%Y%m%d-%H%M%S)"
mkdir -p "$CONFIG_DIR"
SNAPSHOT="$CONFIG_DIR/validated-${STAMP}.env"
cp "$ENV_FILE" "$SNAPSHOT"
ln -sfn "validated-${STAMP}.env" "$CONFIG_DIR/latest.env"
echo "==> 配置已保存: $SNAPSHOT"

# Isaac Sim 宿主机挂载（可选）
OVERRIDE="$ROOT_DIR/docker-compose.override.yml"
if [[ -n "${ISAAC_SIM_PATH:-}" && -d "$ISAAC_SIM_PATH" ]]; then
  cat > "$OVERRIDE" <<EOF
# 由 docker/setup.sh 自动生成 — ISAAC_SIM_PATH 挂载
services:
  replay-isaac:
    volumes:
      - ${ISAAC_SIM_PATH}:/isaac-sim:ro
EOF
  echo "==> Isaac 挂载: $ISAAC_SIM_PATH -> /isaac-sim"
elif [[ -f "$OVERRIDE" ]]; then
  rm -f "$OVERRIDE"
fi

# 构建镜像
cd "$ROOT_DIR"

# NGC 登录（拉取 isaac-sim 基础镜像）
if [[ $BUILD_ISAAC -eq 1 && -n "${NGC_API_KEY:-}" ]]; then
  echo "==> NGC 登录"
  echo "$NGC_API_KEY" | docker login nvcr.io -u '$oauthtoken' --password-stdin
fi

SERVICES=()
[[ $BUILD_MUJOCO -eq 1 ]] && SERVICES+=(replay)
[[ $BUILD_ISAAC -eq 1 ]]  && SERVICES+=(replay-isaac)

echo "==> 构建镜像: ${SERVICES[*]}"
COMPOSE_PROFILES=""
[[ $BUILD_ISAAC -eq 1 ]] && COMPOSE_PROFILES="isaac"
COMPOSE_PROFILES="$COMPOSE_PROFILES" docker compose --env-file "$ENV_FILE" build "${SERVICES[@]}"

# 导出镜像
if [[ $SKIP_EXPORT -eq 0 ]]; then
  mkdir -p "$EXPORT_DIR"
  if [[ $BUILD_MUJOCO -eq 1 ]]; then
    OUT="$EXPORT_DIR/sim-replay-mujoco.tar"
    echo "==> 导出 $IMAGE_MUJOCO -> $OUT"
    docker save "$IMAGE_MUJOCO" -o "$OUT"
  fi
  if [[ $BUILD_ISAAC -eq 1 ]]; then
    OUT="$EXPORT_DIR/sim-replay-isaac.tar"
    echo "==> 导出 $IMAGE_ISAAC -> $OUT"
    docker save "$IMAGE_ISAAC" -o "$OUT"
  fi
  # 记录 manifest
  MANIFEST="$EXPORT_DIR/manifest-${STAMP}.json"
  cat > "$MANIFEST" <<EOF
{
  "timestamp": "$STAMP",
  "backend": "$REPLAY_BACKEND",
  "images": {
    "mujoco": "${BUILD_MUJOCO:+${IMAGE_MUJOCO:-sim-replay:mujoco}}",
    "isaac": "${BUILD_ISAAC:+${IMAGE_ISAAC:-sim-replay:isaac}}"
  },
  "config": "docker/config/validated-${STAMP}.env"
}
EOF
  ln -sfn "manifest-${STAMP}.json" "$EXPORT_DIR/manifest-latest.json"
  echo "==> 镜像清单: $MANIFEST"
fi

# 冒烟测试
if [[ $SKIP_RUN -eq 0 && $BUILD_MUJOCO -eq 1 ]]; then
  echo "==> MuJoCo 冒烟测试: replay inspect"
  docker compose --env-file "$ENV_FILE" run --rm replay inspect /data/eda9cc2192f7.mcap
fi

if [[ $SKIP_RUN -eq 0 && $BUILD_ISAAC -eq 1 ]]; then
  bash "$SCRIPT_DIR/smoke_isaac.sh"
fi

echo ""
echo "完成。配置: $SNAPSHOT"
[[ $SKIP_EXPORT -eq 0 ]] && echo "镜像: $EXPORT_DIR/"
echo "运行回放: docker compose --env-file docker/.env run --rm replay"

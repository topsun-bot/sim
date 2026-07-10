# Docker 指南

## 概述

| 服务 | 镜像 | Profile | 说明 |
|------|------|---------|------|
| `replay` | `sim-replay:mujoco` | 默认 | MuJoCo 物理回放，支持视频导出 |
| `replay-isaac` | `sim-replay:isaac` | `isaac` | 基于 NGC `isaac-sim:5.1.0` |
| `replay-viz` | `sim-replay:mujoco` | `viz` | X11 实时可视化（MuJoCo + OpenCV） |
| `replay-foxglove` | `sim-replay:mujoco` | `foxglove` | Foxglove WebSocket 可视化 |

## 一键部署

```bash
bash docker/setup.sh --backend both   # mujoco + isaac
bash docker/setup.sh --backend mujoco  # 仅 MuJoCo
bash docker/setup.sh --backend isaac --no-export  # 仅 Isaac，跳过 tar 导出
```

流程：

1. 从 `docker/env.example` 生成 `docker/.env`
2. `docker/validate_env.sh` 校验环境变量
3. 保存配置快照 → `docker/config/validated-<时间戳>.env`
4. `docker compose build`
5. `docker save` → `docker/images/*.tar`（可用 `--no-export` 跳过）
6. 冒烟测试（MuJoCo `inspect`；Isaac 见 `docker/smoke_isaac.sh`）

## 环境变量

复制并编辑配置：

```bash
cp docker/env.example docker/.env
```

| 变量 | 默认 | 说明 |
|------|------|------|
| `REPLAY_BACKEND` | `both` | setup 构建目标：`mujoco` / `isaac` / `both` |
| `IMAGE_MUJOCO` | `sim-replay:mujoco` | MuJoCo 镜像标签 |
| `IMAGE_ISAAC` | `sim-replay:isaac` | Isaac 镜像标签 |
| `MUJOCO_GL` | `egl` | 无头渲染：`egl` / `osmesa` / `glfw` |
| `ISAAC_SIM_IMAGE` | `nvcr.io/nvidia/isaac-sim:5.1.0` | Isaac 基础镜像 |
| `ACCEPT_EULA` | `Y` | NGC 许可（Isaac 容器必需） |
| `PRIVACY_CONSENT` | `Y` | 隐私协议（Isaac 容器必需） |
| `NGC_API_KEY` | — | 拉取 NGC 私有镜像时使用 |
| `ISAAC_SIM_PATH` | — | 宿主机 Isaac 安装目录（可选挂载） |
| `NVIDIA_VISIBLE_DEVICES` | `all` | GPU 设备 |
| `IMAGE_EXPORT_DIR` | `./docker/images` | 镜像 tar 导出目录 |

单独校验：

```bash
bash docker/validate_env.sh
```

## 常用命令

```bash
# 检查 MCAP
docker compose --env-file docker/.env run --rm replay \
  inspect /data/eda9cc2192f7.mcap

# MuJoCo 完整回放
docker compose --env-file docker/.env run --rm replay

# Isaac Sim 5.1 回放（GPU）
docker compose --env-file docker/.env --profile isaac run --rm replay-isaac

# Foxglove 可视化（推荐）
docker compose --env-file docker/.env --profile foxglove run --rm -p 8765:8765 replay-foxglove
# Foxglove Studio → Open connection → ws://localhost:8765

# X11 实时可视化（需 DISPLAY）
xhost +local:docker   # 首次授权
docker compose --env-file docker/.env --profile viz run --rm replay-viz

# Isaac 冒烟测试
bash docker/smoke_isaac.sh

# 加载离线镜像
docker load -i docker/images/sim-replay-mujoco.tar
docker load -i docker/images/sim-replay-isaac.tar
```

## Isaac Sim 5.1 说明

- 基础镜像：`nvcr.io/nvidia/isaac-sim:5.1.0`（Python 3.11）
- replay 包通过 `/isaac-sim/python.sh` 安装，启动时加载 `setup_python_env.sh`
- 当前 Isaac 后端为 **MuJoCo 物理委托**（Omniverse 运行时已检测，完整仿真待 Phase 3）
- Isaac profile 默认 `--no-video`，避免 MuJoCo EGL 与 Omniverse GL 冲突

切换 Isaac 版本：修改 `docker/.env` 中 `ISAAC_SIM_IMAGE`，重新执行 `bash docker/setup.sh --backend isaac`。

## 目录

```
docker/
├── env.example          # 配置模板
├── .env                 # 本地配置（gitignore）
├── validate_env.sh      # 环境校验
├── setup.sh             # 一键构建 + 导出 + 测试
├── smoke_isaac.sh       # Isaac profile 冒烟测试
├── config/              # 校验通过的配置快照
├── images/              # 导出的镜像 tar
├── Dockerfile.mujoco
├── Dockerfile.isaac
└── entrypoint.sh
```

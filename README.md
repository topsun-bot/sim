# sim-replay

D1 Leader-Follower MCAP 数据物理闭环回放系统（MuJoCo / Isaac Sim 5.1）。

## 快速开始

### 本地

```bash
pip install -e .
replay inspect data/eda9cc2192f7.mcap
replay run --mcap data/eda9cc2192f7.mcap --meta data/eda9cc2192f7.meta.json
```

### Docker（推荐）

```bash
# 一键：校验环境 → 保存配置 → 构建镜像 → 导出 tar → 冒烟测试
bash docker/setup.sh --backend both

# MuJoCo 回放
docker compose --env-file docker/.env run --rm replay

# Isaac Sim 5.1 回放
docker compose --env-file docker/.env --profile isaac run --rm replay-isaac

# 实时可视化（需 DISPLAY / X11）
docker compose --env-file docker/.env --profile viz run --rm replay-viz
```

### 实时可视化

```bash
# MuJoCo 3D + OpenCV（需 DISPLAY）
replay run -v

# Foxglove Studio（推荐，无需 X11）
replay run --foxglove
# Studio → Open connection → ws://localhost:8765
```

Docker：

```bash
docker compose --env-file docker/.env --profile foxglove run --rm -p 8765:8765 replay-foxglove
```

## 文档

| 文档 | 说明 |
|------|------|
| [数据回放系统方案](doc/数据回放系统方案.md) | 架构、数据格式、分期规划 |
| [API 说明](doc/api.md) | CLI 参数与输出格式 |
| [Docker 指南](doc/docker.md) | 环境变量、镜像构建、冒烟测试 |
| [实施清单](doc/回放系统-实施清单.md) | 进度与命令速查 |

## 输出示例

```
output/<episode_id>/
├── report.json          # sim_success、关节误差、与 meta 对比
├── tracking.csv         # 逐步跟踪数据
├── sim_scene.mp4        # 仿真场景相机
├── sim_wrist.mp4        # 仿真腕部相机
└── compare_combined.mp4 # 左真机 / 右仿真对比
```

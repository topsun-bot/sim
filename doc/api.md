# replay CLI API

## inspect

检查 MCAP 文件结构与首条消息样例。

```bash
replay inspect <mcap_path> [--json]
```

| 参数 | 说明 |
|------|------|
| `mcap_path` | MCAP 文件路径（位置参数） |
| `--json` | 以 JSON 输出 |

## run

执行物理闭环回放。

```bash
replay run \
  --mcap PATH \
  --meta PATH \
  --backend {mujoco,isaac} \
  --source {command,follower,leader} \
  --output DIR \
  [--latency-compensation-ms MS] \
  [--no-video] \
  [--visualize | -v] \
  [--realtime | --fast]
```

### 参数

| 参数 | 默认 | 说明 |
|------|------|------|
| `--mcap` | `data/eda9cc2192f7.mcap` | MCAP 文件路径 |
| `--meta` | 同名 `.meta.json` | Episode 元数据 |
| `--backend` | `mujoco` | 仿真后端：`mujoco` 或 `isaac` |
| `--source` | `command` | 控制源：`command` / `follower` / `leader` |
| `--output` | `./output` | 输出根目录 |
| `--latency-compensation-ms` | `0` | 控制信号提前量（毫秒） |
| `--no-video` | false | 跳过视频导出 |
| `--visualize`, `-v` | false | 回放时实时显示 3D 场景与相机画面 |
| `--realtime` / `--fast` | `--realtime` | 可视化时按真实时间播放；`--fast` 全速 |

### 可视化说明

启用 `-v` 时：

1. **MuJoCo 3D 视窗** — 交互式场景（旋转、缩放）
2. **OpenCV 窗口** — scene + wrist 相机并排显示

要求宿主机设置 `DISPLAY`（本地桌面或 X11 转发）。Docker 见 [Docker 指南](docker.md) 中 `replay-viz` profile。

### 后端差异

| 后端 | 物理引擎 | 视频 | 可视化 |
|------|----------|------|--------|
| `mujoco` | MuJoCo | 支持 | 3D + 相机 |
| `isaac` | MuJoCo 委托（Phase 3 完整 Isaac 待实现） | 建议 `--no-video` | 容器内受限 |

## 输出

```
output/<episode_id>/
├── report.json
├── tracking.csv
├── sim_scene.mp4
├── sim_wrist.mp4
└── compare_combined.mp4
```

### report.json 字段

| 字段 | 说明 |
|------|------|
| `sim_success` | 仿真任务是否成功（橙子入碗 + 夹爪张开） |
| `meta_result` | 真机 episode 标注结果 |
| `joint_rmse_deg` | 关节跟踪 RMSE（度） |
| `max_joint_error_deg` | 单关节最大误差 |
| `sim2real_match` | `sim_success` 与 `meta_result` 是否一致 |
| `final_orange_in_bowl` | 终态橙子是否在碗内 |

# replay CLI API

## inspect

检查 MCAP 文件结构与首条消息样例。

```bash
replay inspect <mcap_path> [--json]
```

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
  [--no-video]
```

### 参数

| 参数 | 默认 | 说明 |
|------|------|------|
| `--mcap` | 必填 | MCAP 文件路径 |
| `--meta` | 可选 | episode meta.json |
| `--backend` | `mujoco` | 仿真后端 |
| `--source` | `command` | 控制数据源 |
| `--output` | `./output` | 输出目录 |
| `--latency-compensation-ms` | `0` | 控制延迟补偿 |
| `--no-video` | false | 跳过视频导出 |

## 输出

```
output/<episode_id>/
├── report.json
├── tracking.csv
├── sim_scene.mp4
├── sim_wrist.mp4
└── compare_combined.mp4
```

# sim-replay

D1 Leader-Follower MCAP 数据物理闭环回放系统（MuJoCo / Isaac Sim）。

## 快速开始

```bash
# 本地
pip install -e .
replay inspect data/eda9cc2192f7.mcap
replay run --mcap data/eda9cc2192f7.mcap --meta data/eda9cc2192f7.meta.json

# Docker
docker compose build replay
docker compose run --rm replay inspect /data/eda9cc2192f7.mcap
docker compose run --rm replay
```

## 文档

- [数据回放系统方案](doc/数据回放系统方案.md)
- [API 说明](doc/api.md)

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from replay.mcap.schemas import EpisodeMeta, SceneSpec


@dataclass
class ReplayConfig:
    mcap_path: Path
    meta_path: Path | None
    backend: str = "mujoco"
    source: str = "command"
    output_dir: Path = Path("output")
    latency_compensation_ms: float = 0.0
    write_video: bool = True
    visualize: bool = False
    foxglove: bool = False
    foxglove_host: str = "0.0.0.0"
    foxglove_port: int = 8765
    realtime: bool = True
    control_hz: float = 30.0

    @property
    def episode_id(self) -> str:
        return self.mcap_path.stem

    def load_meta(self) -> EpisodeMeta:
        if self.meta_path and self.meta_path.is_file():
            with open(self.meta_path) as f:
                return EpisodeMeta.from_json(json.load(f))
        return EpisodeMeta(
            episode_id=self.episode_id,
            scene_id="H2-grasp",
            object_class="orange",
            result="unknown",
            duration_sec=0.0,
            instruction="",
        )

    def scene_spec(self, meta: EpisodeMeta) -> SceneSpec:
        from replay.scenes.registry import get_scene

        return get_scene(meta.scene_id, meta.object_class)


def default_data_paths(root: Path | None = None) -> tuple[Path, Path]:
    root = root or Path("data")
    return root / "eda9cc2192f7.mcap", root / "eda9cc2192f7.meta.json"

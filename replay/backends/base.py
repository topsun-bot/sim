from __future__ import annotations

from typing import Protocol

import numpy as np

from replay.mcap.schemas import SceneSpec, SimObservation


class SimBackend(Protocol):
    def reset(self, scene: SceneSpec) -> None: ...

    def step(self, target_angles_deg: np.ndarray, dt: float) -> SimObservation: ...

    def render(self, camera: str) -> np.ndarray: ...

    def get_object_pose(self, name: str) -> np.ndarray: ...

    def close(self) -> None: ...

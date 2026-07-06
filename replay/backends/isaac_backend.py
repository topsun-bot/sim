from __future__ import annotations

from replay.backends.mujoco_backend import MuJoCoBackend


class IsaacSimBackend:
    """Isaac Sim backend stub — requires Omniverse runtime on GPU host."""

    def __init__(self) -> None:
        self._available = False
        try:
            import omni  # noqa: F401

            self._available = True
        except ImportError:
            pass

    def reset(self, scene) -> None:
        if not self._available:
            raise RuntimeError(
                "Isaac Sim (omni) is not installed. "
                "Use --backend mujoco or run with docker compose --profile isaac on a GPU host."
            )

    def step(self, target_angles_deg, dt):
        raise NotImplementedError("Isaac Sim backend is a Phase 3 placeholder")

    def render(self, camera: str):
        raise NotImplementedError

    def get_object_pose(self, name: str):
        raise NotImplementedError

    def close(self) -> None:
        pass


def create_backend(name: str, enable_render: bool = True) -> MuJoCoBackend | IsaacSimBackend:
    if name == "mujoco":
        return MuJoCoBackend(headless=True, enable_render=enable_render)
    if name == "isaac":
        return IsaacSimBackend()
    raise ValueError(f"Unknown backend: {name}")

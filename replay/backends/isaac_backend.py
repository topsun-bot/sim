from __future__ import annotations

from replay.backends.mujoco_backend import MuJoCoBackend


class IsaacSimBackend:
    """Isaac Sim backend — Omniverse runtime + MuJoCo physics delegate (Phase 3)."""

    def __init__(self, enable_render: bool = True, enable_viewer: bool = False) -> None:
        self._available = False
        self._enable_render = enable_render
        self._enable_viewer = enable_viewer
        self._inner: MuJoCoBackend | None = None
        try:
            import omni  # noqa: F401

            self._available = True
        except ImportError:
            pass

    def reset(self, scene, initial_angles_deg=None) -> None:
        if not self._available:
            raise RuntimeError(
                "Isaac Sim (omni) is not installed. "
                "Use --backend mujoco or run with docker compose --profile isaac on a GPU host."
            )
        need_render = self._enable_render or self._enable_viewer
        self._inner = MuJoCoBackend(
            headless=not self._enable_viewer,
            enable_render=need_render,
            enable_viewer=self._enable_viewer,
        )
        self._inner.reset(scene, initial_angles_deg=initial_angles_deg)

    def open_viewer(self) -> None:
        if self._inner is not None:
            self._inner.open_viewer()

    def sync_viewer(self) -> bool:
        if self._inner is None:
            return True
        return self._inner.sync_viewer()

    def set_joint_positions(self, angles_deg) -> None:
        if self._inner is None:
            raise RuntimeError("Isaac backend not initialized; call reset() first")
        self._inner.set_joint_positions(angles_deg)

    def step(self, target_angles_deg, dt):
        if self._inner is None:
            raise RuntimeError("Isaac backend not initialized; call reset() first")
        return self._inner.step(target_angles_deg, dt)

    def render(self, camera: str):
        if self._inner is None:
            raise RuntimeError("Isaac backend not initialized; call reset() first")
        return self._inner.render(camera)

    def get_object_pose(self, name: str):
        if self._inner is None:
            raise RuntimeError("Isaac backend not initialized; call reset() first")
        return self._inner.get_object_pose(name)

    def close(self) -> None:
        if self._inner is not None:
            self._inner.close()
            self._inner = None


def create_backend(
    name: str,
    enable_render: bool = True,
    enable_viewer: bool = False,
) -> MuJoCoBackend | IsaacSimBackend:
    if name == "mujoco":
        return MuJoCoBackend(
            headless=not enable_viewer,
            enable_render=enable_render,
            enable_viewer=enable_viewer,
        )
    if name == "isaac":
        return IsaacSimBackend(enable_render=enable_render, enable_viewer=enable_viewer)
    raise ValueError(f"Unknown backend: {name}")

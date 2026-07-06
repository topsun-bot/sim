from __future__ import annotations

from replay.backends.mujoco_backend import MuJoCoBackend


class IsaacSimBackend:
    """Isaac Sim backend — Omniverse runtime + MuJoCo physics delegate (Phase 3)."""

    def __init__(self, enable_render: bool = True) -> None:
        self._available = False
        self._enable_render = enable_render
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
        # Isaac 容器内 MuJoCo EGL 渲染与 Omniverse 冲突，物理步进用无渲染模式
        self._inner = MuJoCoBackend(headless=True, enable_render=False)
        self._inner.reset(scene, initial_angles_deg=initial_angles_deg)

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


def create_backend(name: str, enable_render: bool = True) -> MuJoCoBackend | IsaacSimBackend:
    if name == "mujoco":
        return MuJoCoBackend(headless=True, enable_render=enable_render)
    if name == "isaac":
        return IsaacSimBackend(enable_render=enable_render)
    raise ValueError(f"Unknown backend: {name}")

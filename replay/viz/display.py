from __future__ import annotations

import os
import time
import warnings
from typing import Any

import numpy as np


class ReplayDisplay:
    """回放过程实时可视化：MuJoCo 3D 视窗 + 相机画面 OpenCV 窗口。"""

    def __init__(self, realtime: bool = True, show_cameras: bool = True) -> None:
        self.realtime = realtime
        self.show_cameras = show_cameras
        self._cv2: Any = None
        self._win = "sim-replay"
        self._has_viewer = False
        self._last_wall = time.perf_counter()

    @property
    def enabled(self) -> bool:
        return self._has_viewer or self._cv2 is not None

    def open(self, backend) -> None:
        if hasattr(backend, "open_viewer"):
            backend.open_viewer()

        inner = getattr(backend, "_inner", backend)
        if getattr(inner, "_viewer", None) is not None:
            self._has_viewer = True

        if self.show_cameras and os.environ.get("DISPLAY"):
            try:
                import cv2

                self._cv2 = cv2
                self._cv2.namedWindow(self._win, self._cv2.WINDOW_NORMAL)
                self._cv2.resizeWindow(self._win, 1280, 480)
            except Exception as exc:
                warnings.warn(f"OpenCV 窗口不可用: {exc}")

        self._last_wall = time.perf_counter()

    def update(self, backend, t: float, dt: float) -> bool:
        """刷新显示；返回 False 表示用户关闭窗口应中止回放。"""
        if hasattr(backend, "sync_viewer"):
            if not backend.sync_viewer():
                return False

        inner = getattr(backend, "_inner", backend)
        if self._cv2 is not None and hasattr(inner, "render"):
            scene = inner.render("scene")
            wrist = inner.render("wrist")
            if scene.size and wrist.size:
                panel = np.hstack([scene, wrist])
                self._cv2.imshow(self._win, panel)
                key = self._cv2.waitKey(1) & 0xFF
                if key in (27, ord("q")):
                    return False

        if self.realtime:
            elapsed = time.perf_counter() - self._last_wall
            time.sleep(max(0.0, dt - elapsed))
        self._last_wall = time.perf_counter()
        return True

    def close(self) -> None:
        if self._cv2 is not None:
            self._cv2.destroyAllWindows()
            self._cv2 = None
        self._has_viewer = False

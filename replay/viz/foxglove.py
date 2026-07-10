from __future__ import annotations

import asyncio
import base64
import json
import threading
import time
import warnings
from typing import Any

import numpy as np

JOINT_SCHEMA = json.dumps(
    {
        "type": "object",
        "properties": {
            "timestamp_sec": {"type": "number"},
            "j0": {"type": "number"},
            "j1": {"type": "number"},
            "j2": {"type": "number"},
            "j3": {"type": "number"},
            "j4": {"type": "number"},
            "j5": {"type": "number"},
            "j6": {"type": "number"},
        },
    }
)

COMPRESSED_IMAGE_SCHEMA = json.dumps(
    {
        "type": "object",
        "properties": {
            "timestamp": {
                "type": "object",
                "properties": {
                    "sec": {"type": "integer"},
                    "nsec": {"type": "integer"},
                },
            },
            "frame_id": {"type": "string"},
            "format": {"type": "string"},
            "data": {"type": "string", "contentEncoding": "base64"},
        },
    }
)

POSE_SCHEMA = json.dumps(
    {
        "type": "object",
        "properties": {
            "timestamp_sec": {"type": "number"},
            "name": {"type": "string"},
            "x": {"type": "number"},
            "y": {"type": "number"},
            "z": {"type": "number"},
        },
    }
)


def _time_ns(t_sec: float) -> int:
    return int(t_sec * 1_000_000_000)


def _joint_payload(timestamp_sec: float, angles_deg: np.ndarray) -> bytes:
    payload = {"timestamp_sec": round(timestamp_sec, 6)}
    for i in range(7):
        payload[f"j{i}"] = round(float(angles_deg[i]), 4)
    return json.dumps(payload, separators=(",", ":")).encode("utf-8")


def _jpeg_payload(timestamp_sec: float, frame_id: str, bgr: np.ndarray) -> bytes | None:
    import cv2

    ok, buf = cv2.imencode(".jpg", bgr, [int(cv2.IMWRITE_JPEG_QUALITY), 85])
    if not ok:
        return None
    sec = int(timestamp_sec)
    nsec = int((timestamp_sec - sec) * 1_000_000_000)
    payload = {
        "timestamp": {"sec": sec, "nsec": nsec},
        "frame_id": frame_id,
        "format": "jpeg",
        "data": base64.b64encode(buf.tobytes()).decode("ascii"),
    }
    return json.dumps(payload, separators=(",", ":")).encode("utf-8")


def _pose_payload(timestamp_sec: float, name: str, pos: np.ndarray) -> bytes:
    payload = {
        "timestamp_sec": round(timestamp_sec, 6),
        "name": name,
        "x": round(float(pos[0]), 5),
        "y": round(float(pos[1]), 5),
        "z": round(float(pos[2]), 5),
    }
    return json.dumps(payload, separators=(",", ":")).encode("utf-8")


class FoxglovePublisher:
    """Foxglove WebSocket 服务端，回放时发布仿真 topic。"""

    def __init__(
        self,
        host: str = "0.0.0.0",
        port: int = 8765,
        realtime: bool = True,
        image_stride: int = 2,
    ) -> None:
        self.host = host
        self.port = port
        self.realtime = realtime
        self.image_stride = max(1, image_stride)
        self._ready = threading.Event()
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._loop: asyncio.AbstractEventLoop | None = None
        self._server: Any = None
        self._channels: dict[str, int] = {}
        self._last_wall = time.perf_counter()
        self._step = 0
        self._enabled = False

    @property
    def enabled(self) -> bool:
        return self._enabled

    @property
    def url(self) -> str:
        host = "localhost" if self.host in ("0.0.0.0", "::") else self.host
        return f"ws://{host}:{self.port}"

    def start(self) -> None:
        try:
            import foxglove_websocket  # noqa: F401
        except ImportError as exc:
            warnings.warn(
                "foxglove-websocket 未安装，请执行: pip install 'sim-replay[foxglove]'"
            )
            raise RuntimeError("foxglove-websocket not installed") from exc

        self._thread = threading.Thread(target=self._run, name="foxglove-ws", daemon=True)
        self._thread.start()
        if not self._ready.wait(timeout=10.0):
            raise RuntimeError("Foxglove WebSocket server failed to start")
        self._enabled = True
        warnings.warn(f"Foxglove 可视化已启动: {self.url} （Foxglove Studio → Open connection）")

    def _run(self) -> None:
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        try:
            self._loop.run_until_complete(self._serve())
        finally:
            self._loop.close()

    async def _serve(self) -> None:
        from foxglove_websocket.server import FoxgloveServer

        server = FoxgloveServer(self.host, self.port, "sim-replay")
        self._server = server
        server.start()
        await server.wait_opened()

        channels = [
            ("/sim/d1/joint_states", "sim_replay.JointState", JOINT_SCHEMA),
            ("/sim/d1/command", "sim_replay.Command", JOINT_SCHEMA),
            ("/sim/camera/scene/image_raw", "foxglove.CompressedImage", COMPRESSED_IMAGE_SCHEMA),
            ("/sim/camera/wrist/image_raw", "foxglove.CompressedImage", COMPRESSED_IMAGE_SCHEMA),
            ("/sim/objects/orange", "sim_replay.ObjectPose", POSE_SCHEMA),
            ("/sim/objects/bowl", "sim_replay.ObjectPose", POSE_SCHEMA),
        ]
        for topic, schema_name, schema in channels:
            chan_id = await server.add_channel(
                {
                    "topic": topic,
                    "encoding": "json",
                    "schemaName": schema_name,
                    "schema": schema,
                }
            )
            self._channels[topic] = chan_id

        self._ready.set()
        while not self._stop.is_set():
            await asyncio.sleep(0.05)

        server.close()
        await server.wait_closed()

    def update(self, backend, t: float, dt: float, target_deg: np.ndarray, obs) -> None:
        if not self._enabled or self._loop is None or self._server is None:
            return

        ts = _time_ns(t)
        inner = getattr(backend, "_inner", backend)
        self._publish("/sim/d1/joint_states", ts, _joint_payload(t, obs.joint_pos_deg))
        self._publish("/sim/d1/command", ts, _joint_payload(t, target_deg))
        self._publish("/sim/objects/orange", ts, _pose_payload(t, "orange", obs.orange_pos))
        self._publish("/sim/objects/bowl", ts, _pose_payload(t, "bowl", obs.bowl_pos))

        if hasattr(inner, "render") and self._step % self.image_stride == 0:
            scene = inner.render("scene")
            wrist = inner.render("wrist")
            if scene.size:
                payload = _jpeg_payload(t, "scene_cam", scene)
                if payload:
                    self._publish("/sim/camera/scene/image_raw", ts, payload)
            if wrist.size:
                payload = _jpeg_payload(t, "wrist_cam", wrist)
                if payload:
                    self._publish("/sim/camera/wrist/image_raw", ts, payload)

        if self.realtime:
            elapsed = time.perf_counter() - self._last_wall
            time.sleep(max(0.0, dt - elapsed))
        self._last_wall = time.perf_counter()
        self._step += 1

    def _publish(self, topic: str, timestamp_ns: int, payload: bytes) -> None:
        chan_id = self._channels.get(topic)
        if chan_id is None or self._loop is None or self._server is None:
            return
        asyncio.run_coroutine_threadsafe(
            self._server.send_message(chan_id, timestamp_ns, payload),
            self._loop,
        )

    def close(self) -> None:
        if not self._enabled:
            return
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=5.0)
        self._enabled = False

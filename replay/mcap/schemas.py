from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np

JOINT_NAMES = ["j0", "j1", "j2", "j3", "j4", "j5", "j6"]


@dataclass
class JointState:
    timestamp_sec: float
    angles_deg: np.ndarray  # shape (7,)

    @classmethod
    def from_deg_list(cls, timestamp_sec: float, angles: list[float] | tuple[float, ...]) -> JointState:
        return cls(timestamp_sec=timestamp_sec, angles_deg=np.array(angles, dtype=np.float64))

    def to_dict(self) -> dict[str, Any]:
        return {
            "timestamp_sec": self.timestamp_sec,
            **{name: float(self.angles_deg[i]) for i, name in enumerate(JOINT_NAMES)},
        }


@dataclass
class CommandMessage:
    timestamp_sec: float
    seq: int
    funcode: int
    angles_deg: np.ndarray

    @classmethod
    def from_json_payload(cls, timestamp_sec: float, payload: dict[str, Any]) -> CommandMessage:
        data = payload.get("data", payload)
        angles = np.array(
            [float(data[f"angle{i}"]) for i in range(7)],
            dtype=np.float64,
        )
        return cls(
            timestamp_sec=timestamp_sec,
            seq=int(payload.get("seq", 0)),
            funcode=int(payload.get("funcode", 0)),
            angles_deg=angles,
        )


@dataclass
class ImageFrame:
    timestamp_sec: float
    camera: str
    jpeg_bytes: bytes

    def decode_bgr(self) -> np.ndarray:
        import cv2

        arr = np.frombuffer(self.jpeg_bytes, dtype=np.uint8)
        img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
        if img is None:
            raise ValueError("Failed to decode JPEG frame")
        return img


@dataclass
class EpisodeMeta:
    episode_id: str
    scene_id: str
    object_class: str
    result: str
    duration_sec: float
    instruction: str
    raw: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_json(cls, data: dict[str, Any]) -> EpisodeMeta:
        lang = data.get("language", {})
        return cls(
            episode_id=data.get("episode_id", "unknown"),
            scene_id=data.get("platform_profile", {}).get("scene_id", "H2-grasp"),
            object_class=data.get("object_class", "orange"),
            result=data.get("result", "unknown"),
            duration_sec=float(data.get("duration_sec", 0.0)),
            instruction=lang.get("instruction", ""),
            raw=data,
        )


@dataclass
class SceneSpec:
    scene_id: str
    object_class: str
    table_height_m: float = 0.75
    orange_pos: tuple[float, float, float] = (0.32, 0.08, 0.79)
    bowl_pos: tuple[float, float, float] = (0.28, 0.12, 0.755)
    orange_radius_m: float = 0.035
    bowl_radius_m: float = 0.06


@dataclass
class SimObservation:
    joint_pos_deg: np.ndarray
    orange_pos: np.ndarray
    bowl_pos: np.ndarray
    gripper_closed: bool


@dataclass
class ReplayReport:
    episode_id: str
    backend: str
    source: str
    meta_result: str
    sim_success: bool
    duration_sec: float
    joint_rmse_deg: float
    max_joint_error_deg: float
    final_orange_in_bowl: bool
    sim2real_match: bool
    extra: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "episode_id": self.episode_id,
            "backend": self.backend,
            "source": self.source,
            "meta_result": self.meta_result,
            "sim_success": self.sim_success,
            "duration_sec": self.duration_sec,
            "joint_rmse_deg": self.joint_rmse_deg,
            "max_joint_error_deg": self.max_joint_error_deg,
            "final_orange_in_bowl": self.final_orange_in_bowl,
            "sim2real_match": self.sim2real_match,
            **self.extra,
        }

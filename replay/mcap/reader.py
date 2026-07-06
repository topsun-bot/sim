from __future__ import annotations

import json
import re
import struct
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np
from mcap.reader import make_reader

from replay.mcap.schemas import CommandMessage, ImageFrame, JointState

TOPIC_JOINT_STATES = "/d1/joint_states"
TOPIC_COMMAND = "/d1/command"
TOPIC_FOLLOWER = "/d1/follower_joint_states"
TOPIC_SCENE_IMAGE = "/camera/scene/image_raw"
TOPIC_WRIST_IMAGE = "/camera/wrist/image_raw"

JOINT_TOPICS = {TOPIC_JOINT_STATES, TOPIC_FOLLOWER}
IMAGE_TOPICS = {TOPIC_SCENE_IMAGE, TOPIC_WRIST_IMAGE}


def _ns_to_sec(ns: int) -> float:
    return ns / 1e9


def decode_joint_binary(data: bytes) -> np.ndarray:
    """Decode PubServoInfo_ DDS payload: 4-byte header + 7 float32 angles (degrees)."""
    if len(data) < 32:
        raise ValueError(f"Joint payload too short: {len(data)} bytes")
    return np.array(struct.unpack("<7f", data[4:32]), dtype=np.float64)


def decode_command_binary(data: bytes) -> dict[str, Any]:
    """Decode ArmString_ payload containing JSON command."""
    text = data.decode("latin-1", errors="ignore")
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        raise ValueError("No JSON found in command payload")
    return json.loads(match.group())


@dataclass
class ChannelInfo:
    topic: str
    schema_name: str | None
    encoding: str | None
    message_count: int = 0


@dataclass
class InspectResult:
    mcap_path: str
    channels: list[ChannelInfo]
    duration_sec: float
    time_start_sec: float
    time_end_sec: float
    samples: dict[str, Any] = field(default_factory=dict)


@dataclass
class EpisodeRecording:
    mcap_path: Path
    joint_states: list[JointState] = field(default_factory=list)
    commands: list[CommandMessage] = field(default_factory=list)
    follower_states: list[JointState] = field(default_factory=list)
    scene_images: list[ImageFrame] = field(default_factory=list)
    wrist_images: list[ImageFrame] = field(default_factory=list)

    @property
    def anchor_states(self) -> list[JointState]:
        return self.joint_states


def inspect_mcap(mcap_path: Path) -> InspectResult:
    channels: dict[str, ChannelInfo] = {}
    samples: dict[str, Any] = {}
    time_start: float | None = None
    time_end: float | None = None

    with open(mcap_path, "rb") as f:
        reader = make_reader(f)
        summary = reader.get_summary()
        schemas = {s.id: s for s in (summary.schemas or {}).values()}
        for ch in (summary.channels or {}).values():
            schema = schemas.get(ch.schema_id)
            channels[ch.topic] = ChannelInfo(
                topic=ch.topic,
                schema_name=schema.name if schema else None,
                encoding=schema.encoding if schema else None,
            )

    with open(mcap_path, "rb") as f:
        reader = make_reader(f)
        for _schema, channel, message in reader.iter_messages():
            info = channels[channel.topic]
            info.message_count += 1
            t = _ns_to_sec(message.log_time)
            time_start = t if time_start is None else min(time_start, t)
            time_end = t if time_end is None else max(time_end, t)

            if channel.topic not in samples:
                samples[channel.topic] = _decode_sample(channel.topic, message.data, t)

    duration = (time_end or 0.0) - (time_start or 0.0)
    return InspectResult(
        mcap_path=str(mcap_path),
        channels=sorted(channels.values(), key=lambda c: c.topic),
        duration_sec=duration,
        time_start_sec=time_start or 0.0,
        time_end_sec=time_end or 0.0,
        samples=samples,
    )


def _decode_sample(topic: str, data: bytes, timestamp_sec: float) -> Any:
    if topic in JOINT_TOPICS:
        angles = decode_joint_binary(data)
        return JointState(timestamp_sec=timestamp_sec, angles_deg=angles).to_dict()
    if topic == TOPIC_COMMAND:
        payload = decode_command_binary(data)
        cmd = CommandMessage.from_json_payload(timestamp_sec, payload)
        return {
            "timestamp_sec": cmd.timestamp_sec,
            "seq": cmd.seq,
            "funcode": cmd.funcode,
            "angles_deg": cmd.angles_deg.tolist(),
        }
    if topic in IMAGE_TOPICS:
        return {
            "timestamp_sec": timestamp_sec,
            "jpeg_bytes_len": len(data),
            "format": "jpeg",
        }
    return {"raw_len": len(data)}


def load_episode(mcap_path: Path) -> EpisodeRecording:
    rec = EpisodeRecording(mcap_path=mcap_path)

    with open(mcap_path, "rb") as f:
        reader = make_reader(f)
        for _schema, channel, message in reader.iter_messages():
            t = _ns_to_sec(message.log_time)
            topic = channel.topic
            data = message.data

            if topic == TOPIC_JOINT_STATES:
                rec.joint_states.append(
                    JointState(timestamp_sec=t, angles_deg=decode_joint_binary(data))
                )
            elif topic == TOPIC_FOLLOWER:
                rec.follower_states.append(
                    JointState(timestamp_sec=t, angles_deg=decode_joint_binary(data))
                )
            elif topic == TOPIC_COMMAND:
                payload = decode_command_binary(data)
                rec.commands.append(CommandMessage.from_json_payload(t, payload))
            elif topic == TOPIC_SCENE_IMAGE:
                rec.scene_images.append(
                    ImageFrame(timestamp_sec=t, camera="scene", jpeg_bytes=bytes(data))
                )
            elif topic == TOPIC_WRIST_IMAGE:
                rec.wrist_images.append(
                    ImageFrame(timestamp_sec=t, camera="wrist", jpeg_bytes=bytes(data))
                )

    for lst in (
        rec.joint_states,
        rec.commands,
        rec.follower_states,
        rec.scene_images,
        rec.wrist_images,
    ):
        lst.sort(key=lambda x: x.timestamp_sec)

    return rec

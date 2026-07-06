from __future__ import annotations

from pathlib import Path

import pytest

from replay.mcap.reader import decode_command_binary, decode_joint_binary, inspect_mcap, load_episode

DATA_DIR = Path(__file__).resolve().parents[1] / "data"
MCAP = DATA_DIR / "eda9cc2192f7.mcap"


@pytest.mark.skipif(not MCAP.is_file(), reason="sample mcap missing")
def test_inspect_mcap():
    result = inspect_mcap(MCAP)
    assert result.duration_sec > 5
    topics = {c.topic for c in result.channels}
    assert "/d1/command" in topics
    assert "/camera/scene/image_raw" in topics


@pytest.mark.skipif(not MCAP.is_file(), reason="sample mcap missing")
def test_load_episode_counts():
    rec = load_episode(MCAP)
    assert len(rec.joint_states) == 322
    assert len(rec.commands) == 106
    assert len(rec.scene_images) == 305


@pytest.mark.skipif(not MCAP.is_file(), reason="sample mcap missing")
def test_decode_joint_binary():
    rec = load_episode(MCAP)
    angles = rec.joint_states[0].angles_deg
    assert angles.shape == (7,)
    assert -180 < angles[0] < 180


@pytest.mark.skipif(not MCAP.is_file(), reason="sample mcap missing")
def test_decode_command():
    rec = load_episode(MCAP)
    cmd = rec.commands[0]
    assert cmd.funcode == 2
    assert cmd.angles_deg.shape == (7,)


def test_decode_command_binary_static():
  raw = b'\x00\x01\x00\x00\xa6\x00\x00\x00{"seq":4,"address":1,"funcode":2,"data":{"mode":0,"angle0":-15.800,"angle1":-21.100,"angle2":12.300,"angle3":-1.600,"angle4":61.500,"angle5":12.400,"angle6":49.900}}\x00'
  payload = decode_command_binary(raw)
  assert payload["funcode"] == 2
  assert payload["data"]["angle0"] == -15.8


def test_decode_joint_binary_static():
    import struct
    vals = [-15.8, -22.1, 11.6, -1.6, 62.9, 13.4, 49.9]
    raw = b"\x00\x01\x00\x00" + struct.pack("<7f", *vals)
    decoded = decode_joint_binary(raw)
    assert len(decoded) == 7
    assert abs(decoded[0] - (-15.8)) < 0.01

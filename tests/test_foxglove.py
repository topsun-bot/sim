from __future__ import annotations

import json

import numpy as np

from replay.viz.foxglove import _joint_payload, _pose_payload


def test_joint_payload():
    raw = _joint_payload(1.5, np.array([1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0]))
    data = json.loads(raw)
    assert data["timestamp_sec"] == 1.5
    assert data["j0"] == 1.0
    assert data["j6"] == 7.0


def test_pose_payload():
    raw = _pose_payload(0.5, "orange", np.array([0.32, 0.08, 0.79]))
    data = json.loads(raw)
    assert data["name"] == "orange"
    assert abs(data["x"] - 0.32) < 1e-4

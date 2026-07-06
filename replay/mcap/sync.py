from __future__ import annotations

import bisect
from typing import Generic, Sequence, TypeVar

import numpy as np

from replay.mcap.schemas import CommandMessage, JointState

T = TypeVar("T")


class TimestampedSequence(Generic[T]):
    """Sorted sequence with timestamp_sec attribute on each item."""

    def __init__(self, items: Sequence[T]) -> None:
        self.items = list(items)
        self.timestamps = [float(getattr(i, "timestamp_sec")) for i in self.items]

    def __len__(self) -> int:
        return len(self.items)

    def nearest(self, t: float) -> T | None:
        if not self.items:
            return None
        idx = bisect.bisect_left(self.timestamps, t)
        if idx == 0:
            return self.items[0]
        if idx >= len(self.items):
            return self.items[-1]
        before = self.items[idx - 1]
        after = self.items[idx]
        if abs(self.timestamps[idx] - t) < abs(self.timestamps[idx - 1] - t):
            return after
        return before

    def interpolate_joint_angles(self, t: float) -> np.ndarray | None:
        if not self.items:
            return None
        if t <= self.timestamps[0]:
            return np.array(getattr(self.items[0], "angles_deg"), dtype=np.float64)
        if t >= self.timestamps[-1]:
            return np.array(getattr(self.items[-1], "angles_deg"), dtype=np.float64)

        idx = bisect.bisect_right(self.timestamps, t)
        before = self.items[idx - 1]
        after = self.items[idx]
        t0, t1 = self.timestamps[idx - 1], self.timestamps[idx]
        alpha = (t - t0) / (t1 - t0) if t1 > t0 else 0.0
        a0 = np.array(getattr(before, "angles_deg"), dtype=np.float64)
        a1 = np.array(getattr(after, "angles_deg"), dtype=np.float64)
        return a0 + alpha * (a1 - a0)


def build_control_timeline(
    commands: Sequence[CommandMessage],
    follower_states: Sequence[JointState],
    source: str,
) -> list[tuple[float, np.ndarray]]:
    """Return (timestamp, target_angles_deg) pairs for replay."""
    if source == "command":
        return [(c.timestamp_sec, c.angles_deg.copy()) for c in commands]
    if source == "follower":
        return [(s.timestamp_sec, s.angles_deg.copy()) for s in follower_states]
    if source == "leader":
        raise ValueError("leader source is reference-only; use command or follower for physics replay")
    raise ValueError(f"Unknown source: {source}")

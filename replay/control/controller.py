from __future__ import annotations

import numpy as np


def apply_latency_compensation(
    timeline: list[tuple[float, np.ndarray]],
    compensation_ms: float,
) -> list[tuple[float, np.ndarray]]:
    if compensation_ms <= 0:
        return timeline
    shift = compensation_ms / 1000.0
    return [(max(0.0, t - shift), angles) for t, angles in timeline]

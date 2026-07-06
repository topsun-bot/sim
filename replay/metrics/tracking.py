from __future__ import annotations

import csv
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np


@dataclass
class TrackingAccumulator:
    rows: list[dict] = field(default_factory=list)
    _sq_errors: list[float] = field(default_factory=list)
    _max_errors: list[float] = field(default_factory=list)

    @property
    def count(self) -> int:
        return len(self.rows)

    def add(self, t: float, target_deg: np.ndarray, actual_deg: np.ndarray) -> None:
        err = actual_deg - target_deg
        rmse_step = float(np.sqrt(np.mean(err**2)))
        max_step = float(np.max(np.abs(err)))
        self._sq_errors.append(rmse_step**2)
        self._max_errors.append(max_step)
        self.rows.append(
            {
                "time_sec": round(t, 4),
                "joint_rmse_deg": round(rmse_step, 4),
                "joint_max_error_deg": round(max_step, 4),
                **{f"target_j{i}": round(float(target_deg[i]), 3) for i in range(7)},
                **{f"actual_j{i}": round(float(actual_deg[i]), 3) for i in range(7)},
            }
        )

    def rmse(self) -> float:
        if not self._sq_errors:
            return 0.0
        return float(np.sqrt(np.mean(self._sq_errors)))

    def max_error(self) -> float:
        if not self._max_errors:
            return 0.0
        return float(np.max(self._max_errors))

    def write_csv(self, path: Path) -> None:
        if not self.rows:
            return
        with open(path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=list(self.rows[0].keys()))
            writer.writeheader()
            writer.writerows(self.rows)

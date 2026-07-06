from __future__ import annotations

import numpy as np


def check_orange_in_bowl(
    orange_pos: np.ndarray,
    bowl_pos: np.ndarray,
    bowl_radius_m: float,
    height_tol_m: float = 0.05,
) -> bool:
    xy_dist = float(np.linalg.norm(orange_pos[:2] - bowl_pos[:2]))
    z_ok = orange_pos[2] >= bowl_pos[2] - 0.01 and orange_pos[2] <= bowl_pos[2] + height_tol_m
    return xy_dist < bowl_radius_m * 0.8 and z_ok


def check_task_success(in_bowl: bool, gripper_open: bool) -> bool:
    return in_bowl and gripper_open

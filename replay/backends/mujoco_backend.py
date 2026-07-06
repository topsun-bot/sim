from __future__ import annotations

import os
from pathlib import Path

import numpy as np

from replay.mcap.schemas import SceneSpec, SimObservation

JOINT_NAMES = ["j0", "j1", "j2", "j3", "j4", "j5", "j6"]
J6_OPEN_DEG = -40.0
J6_CLOSE_DEG = 20.0
J6_OPEN_M = -0.028
J6_CLOSE_M = 0.012

ASSETS_DIR = Path(__file__).resolve().parents[2] / "assets" / "mujoco"
MJCF_PATH = ASSETS_DIR / "d1_replay.xml"


def map_d1_gripper_deg(angle6: float) -> float:
    """Map D1 servo gripper reading to MuJoCo j6 hinge degrees."""
    if J6_OPEN_DEG <= angle6 <= J6_CLOSE_DEG:
        return angle6
    # Observed teleop data uses ~0-60 servo scale (50 ≈ neutral)
    return float(np.interp(angle6, [0.0, 60.0], [J6_CLOSE_DEG, J6_OPEN_DEG]))


def j6_deg_to_slide(j6_deg: float) -> float:
    j6_deg = map_d1_gripper_deg(j6_deg)
    ratio = (J6_CLOSE_DEG - j6_deg) / (J6_CLOSE_DEG - J6_OPEN_DEG)
    ratio = float(np.clip(ratio, 0.0, 1.0))
    return J6_OPEN_M + ratio * (J6_CLOSE_M - J6_OPEN_M)


def j6_slide_to_deg(slide_m: float) -> float:
    ratio = (slide_m - J6_OPEN_M) / (J6_CLOSE_M - J6_OPEN_M)
    ratio = float(np.clip(ratio, 0.0, 1.0))
    return J6_CLOSE_DEG - ratio * (J6_CLOSE_DEG - J6_OPEN_DEG)


class MuJoCoBackend:
    def __init__(self, headless: bool = True, enable_render: bool = True) -> None:
        import mujoco

        if headless and "MUJOCO_GL" not in os.environ:
            os.environ.setdefault("MUJOCO_GL", "egl")

        self._mujoco = mujoco
        self._enable_render = enable_render
        self.model = mujoco.MjModel.from_xml_path(str(MJCF_PATH))
        self.data = mujoco.MjData(self.model)
        self.renderer = None
        if enable_render:
            self._init_renderer()
        self._scene = SceneSpec(scene_id="H2-grasp", object_class="orange")
        self._actuator_ids = [
            mujoco.mj_name2id(self.model, mujoco.mjtObj.mjOBJ_ACTUATOR, f"a_{n}")
            for n in JOINT_NAMES
        ]
        self._orange_body = mujoco.mj_name2id(self.model, mujoco.mjtObj.mjOBJ_BODY, "orange")
        self._bowl_body = mujoco.mj_name2id(self.model, mujoco.mjtObj.mjOBJ_BODY, "bowl")
        self._ee_body = mujoco.mj_name2id(self.model, mujoco.mjtObj.mjOBJ_BODY, "ee")
        self._camera_map = {
            "scene": mujoco.mj_name2id(self.model, mujoco.mjtObj.mjOBJ_CAMERA, "scene_cam"),
            "wrist": mujoco.mj_name2id(self.model, mujoco.mjtObj.mjOBJ_CAMERA, "wrist_cam"),
        }
        self._grasp_attached = False
        self._grasp_offset = np.zeros(3)

    def _init_renderer(self) -> None:
        import mujoco

        backends = [os.environ.get("MUJOCO_GL", "egl"), "osmesa"]
        last_err: Exception | None = None
        for backend in backends:
            try:
                os.environ["MUJOCO_GL"] = backend
                self.renderer = mujoco.Renderer(self.model, 480, 640)
                return
            except Exception as exc:
                last_err = exc
                self.renderer = None
        self._enable_render = False
        if last_err:
            import warnings

            warnings.warn(f"MuJoCo renderer disabled: {last_err}")

    def reset(self, scene: SceneSpec, initial_angles_deg: np.ndarray | None = None) -> None:
        mujoco = self._mujoco
        mujoco.mj_resetData(self.model, self.data)

        self._scene = scene
        self._set_body_pos("orange", np.array(scene.orange_pos, dtype=np.float64))
        self._set_body_pos("bowl", np.array(scene.bowl_pos, dtype=np.float64))
        self._grasp_attached = False
        self._grasp_offset = np.zeros(3)

        if initial_angles_deg is not None:
            self.set_joint_positions(initial_angles_deg)

        for _ in range(50):
            mujoco.mj_step(self.model, self.data)

    def set_joint_positions(self, angles_deg: np.ndarray) -> None:
        mujoco = self._mujoco
        ctrl = self._angles_to_ctrl(angles_deg)
        for i, name in enumerate(JOINT_NAMES):
            adr = self.model.joint(name).qposadr[0]
            if i < 6:
                self.data.qpos[adr] = float(angles_deg[i])
            else:
                self.data.qpos[adr] = float(ctrl[i])
        self.data.ctrl[:] = ctrl
        self.data.qvel[:] = 0
        mujoco.mj_forward(self.model, self.data)

    def _set_body_pos(self, name: str, pos: np.ndarray) -> None:
        bid = self._mujoco.mj_name2id(self.model, self._mujoco.mjtObj.mjOBJ_BODY, name)
        if self.model.body_jntnum[bid] > 0:
            jnt_adr = self.model.body_jntadr[bid]
            qpos_adr = self.model.jnt_qposadr[jnt_adr]
            self.data.qpos[qpos_adr : qpos_adr + 3] = pos
            self.data.qpos[qpos_adr + 3 : qpos_adr + 7] = [1, 0, 0, 0]

    def _angles_to_ctrl(self, angles_deg: np.ndarray) -> np.ndarray:
        ctrl = angles_deg.copy()
        ctrl[6] = j6_deg_to_slide(float(angles_deg[6]))
        return ctrl

    def step(self, target_angles_deg: np.ndarray, dt: float) -> SimObservation:
        mujoco = self._mujoco
        ctrl = self._angles_to_ctrl(target_angles_deg)
        self.data.ctrl[:] = ctrl

        steps = max(1, int(round(dt / self.model.opt.timestep)))
        for _ in range(steps):
            self._update_grasp()
            mujoco.mj_step(self.model, self.data)

        joint_pos = np.array([self.data.qpos[self.model.joint(n).qposadr[0]] for n in JOINT_NAMES])
        joint_pos[6] = j6_slide_to_deg(joint_pos[6])

        orange_pos = self.get_object_pose("orange")
        bowl_pos = self.get_object_pose("bowl")
        gripper_deg = map_d1_gripper_deg(float(target_angles_deg[6]))
        gripper_closed = gripper_deg > -5.0

        return SimObservation(
            joint_pos_deg=joint_pos,
            orange_pos=orange_pos,
            bowl_pos=bowl_pos,
            gripper_closed=gripper_closed,
        )

    def _update_grasp(self) -> None:
        mujoco = self._mujoco
        ee_pos = self.data.xpos[self._ee_body].copy()
        orange_pos = self.data.xpos[self._orange_body].copy()
        dist = float(np.linalg.norm(ee_pos - orange_pos))
        j6_deg = j6_slide_to_deg(float(self.data.qpos[self.model.joint("j6").qposadr[0]]))
        gripper_closed = j6_deg < 15.0

        if not self._grasp_attached and gripper_closed and dist < 0.06:
            self._grasp_attached = True
            self._grasp_offset = orange_pos - ee_pos

        if self._grasp_attached:
            if not gripper_closed:
                self._grasp_attached = False
            else:
                target = ee_pos + self._grasp_offset
                jnt_adr = self.model.body_jntadr[self._orange_body]
                qpos_adr = self.model.jnt_qposadr[jnt_adr]
                self.data.qpos[qpos_adr : qpos_adr + 3] = target
                self.data.qvel[qpos_adr : qpos_adr + 3] = 0

    def render(self, camera: str) -> np.ndarray:
        if self.renderer is None:
            return np.zeros((480, 640, 3), dtype=np.uint8)
        cam_id = self._camera_map.get(camera, self._camera_map["scene"])
        self.renderer.update_scene(self.data, camera=cam_id)
        rgb = self.renderer.render()
        return rgb[:, :, ::-1].copy()

    def get_object_pose(self, name: str) -> np.ndarray:
        bid = self._mujoco.mj_name2id(self.model, self._mujoco.mjtObj.mjOBJ_BODY, name)
        return self.data.xpos[bid].copy()

    def close(self) -> None:
        if self.renderer is not None:
            del self.renderer
            self.renderer = None

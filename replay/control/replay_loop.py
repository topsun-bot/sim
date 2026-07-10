from __future__ import annotations

import csv
import json
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

from replay.backends import create_backend
from replay.config import ReplayConfig
from replay.control.controller import apply_latency_compensation
from replay.mcap.reader import EpisodeRecording, load_episode
from replay.mcap.schemas import EpisodeMeta, ReplayReport
from replay.mcap.sync import TimestampedSequence, build_control_timeline
from replay.metrics.report import write_compare_video, write_sim_videos
from replay.metrics.success import check_orange_in_bowl, check_task_success
from replay.metrics.tracking import TrackingAccumulator
from replay.viz.display import ReplayDisplay
from replay.viz.foxglove import FoxglovePublisher
import warnings


@dataclass
class ReplayResult:
    report: ReplayReport
    output_dir: Path
    tracking_rows: list[dict] = field(default_factory=list)


def run_replay(config: ReplayConfig) -> ReplayResult:
    recording = load_episode(config.mcap_path)
    meta = config.load_meta()
    scene = config.scene_spec(meta)

    timeline = build_control_timeline(
        recording.commands,
        recording.follower_states,
        config.source,
    )
    timeline = apply_latency_compensation(timeline, config.latency_compensation_ms)
    if not timeline:
        raise RuntimeError(f"No control messages for source={config.source!r}")

    t0 = timeline[0][0]
    timeline = [(t - t0, angles) for t, angles in timeline]

    need_render = config.write_video or config.visualize or config.foxglove
    backend = create_backend(
        config.backend,
        enable_render=need_render,
        enable_viewer=config.visualize,
    )
    backend.reset(scene, initial_angles_deg=timeline[0][1])

    display: ReplayDisplay | None = None
    foxglove_pub: FoxglovePublisher | None = None

    if config.foxglove:
        try:
            foxglove_pub = FoxglovePublisher(
                host=config.foxglove_host,
                port=config.foxglove_port,
                realtime=config.realtime,
            )
            foxglove_pub.start()
        except RuntimeError as exc:
            warnings.warn(f"Foxglove 不可用: {exc}")

    if config.visualize:
        display = ReplayDisplay(realtime=config.realtime and foxglove_pub is None)
        display.open(backend)
        if not display.enabled:
            warnings.warn("本地可视化不可用（无 DISPLAY），继续无界面回放")
            display.close()
            display = None

    dt = 1.0 / config.control_hz
    tracker = TrackingAccumulator()
    scene_frames: list[np.ndarray] = []
    wrist_frames: list[np.ndarray] = []

    t_end = timeline[-1][0]
    cmd_idx = 0
    current_target = timeline[0][1]
    t = 0.0
    last_obs = None

    while t <= t_end + dt * 0.5:
        while cmd_idx + 1 < len(timeline) and timeline[cmd_idx + 1][0] <= t:
            cmd_idx += 1
            current_target = timeline[cmd_idx][1]

        obs = backend.step(current_target, dt)
        last_obs = obs
        tracker.add(t, current_target, obs.joint_pos_deg)

        if config.write_video and int(t * config.control_hz) % 2 == 0:
            scene_frames.append(backend.render("scene"))
            wrist_frames.append(backend.render("wrist"))

        if foxglove_pub is not None:
            foxglove_pub.update(backend, t, dt, current_target, obs)

        if display is not None and not display.update(backend, t, dt):
            break

        t += dt

    orange_pos = backend.get_object_pose("orange")
    bowl_pos = backend.get_object_pose("bowl")
    in_bowl = check_orange_in_bowl(orange_pos, bowl_pos, scene.bowl_radius_m)
    gripper_open = not last_obs.gripper_closed if last_obs is not None else True
    sim_success = check_task_success(in_bowl, gripper_open=gripper_open)

    meta_success = meta.result.lower() == "success"
    report = ReplayReport(
        episode_id=meta.episode_id,
        backend=config.backend,
        source=config.source,
        meta_result=meta.result,
        sim_success=sim_success,
        duration_sec=t_end,
        joint_rmse_deg=tracker.rmse(),
        max_joint_error_deg=tracker.max_error(),
        final_orange_in_bowl=in_bowl,
        sim2real_match=(sim_success == meta_success),
        extra={
            "instruction": meta.instruction,
            "scene_id": meta.scene_id,
            "object_class": meta.object_class,
            "control_steps": tracker.count,
        },
    )

    output_dir = config.output_dir / meta.episode_id
    output_dir.mkdir(parents=True, exist_ok=True)

    with open(output_dir / "report.json", "w") as f:
        json.dump(report.to_dict(), f, indent=2)

    tracker.write_csv(output_dir / "tracking.csv")

    if config.write_video:
        write_sim_videos(output_dir, scene_frames, wrist_frames, fps=config.control_hz / 2)
        write_compare_video(
            output_dir,
            recording,
            scene_frames,
            wrist_frames,
            fps=config.control_hz / 2,
            t0=recording.commands[0].timestamp_sec if recording.commands else 0.0,
        )

    if display is not None:
        display.close()
    if foxglove_pub is not None:
        foxglove_pub.close()

    backend.close()

    return ReplayResult(
        report=report,
        output_dir=output_dir,
        tracking_rows=tracker.rows,
    )

from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np

from replay.mcap.reader import EpisodeRecording
from replay.mcap.sync import TimestampedSequence


def write_sim_videos(
    output_dir: Path,
    scene_frames: list[np.ndarray],
    wrist_frames: list[np.ndarray],
    fps: float = 15.0,
) -> None:
    if scene_frames:
        _write_mp4(output_dir / "sim_scene.mp4", scene_frames, fps)
    if wrist_frames:
        _write_mp4(output_dir / "sim_wrist.mp4", wrist_frames, fps)


def write_compare_video(
    output_dir: Path,
    recording: EpisodeRecording,
    sim_scene_frames: list[np.ndarray],
    sim_wrist_frames: list[np.ndarray],
    fps: float = 15.0,
    t0: float = 0.0,
) -> None:
    scene_seq = TimestampedSequence(recording.scene_images)
    wrist_seq = TimestampedSequence(recording.wrist_images)

    if not sim_scene_frames:
        return

    combined: list[np.ndarray] = []
    n = len(sim_scene_frames)
    if recording.commands:
        t_start = recording.commands[0].timestamp_sec - t0
        t_end = recording.commands[-1].timestamp_sec - t0
    else:
        t_start, t_end = 0.0, float(n)
    duration = max(t_end - t_start, 0.001)

    for i in range(n):
        t = t_start + (i / max(n - 1, 1)) * duration + t0
        real_scene = scene_seq.nearest(t)
        real_wrist = wrist_seq.nearest(t)
        sim_s = sim_scene_frames[i]
        sim_w = sim_wrist_frames[i] if i < len(sim_wrist_frames) else sim_s

        top = _hstack_resize(
            real_scene.decode_bgr() if real_scene else _blank(sim_s),
            sim_s,
        )
        bottom = _hstack_resize(
            real_wrist.decode_bgr() if real_wrist else _blank(sim_w),
            sim_w,
        )
        combined.append(_vstack([top, bottom]))

    _write_mp4(output_dir / "compare_combined.mp4", combined, fps)


def _blank(ref: np.ndarray) -> np.ndarray:
    return np.zeros_like(ref)


def _hstack_resize(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    h = min(a.shape[0], b.shape[0])
    a = cv2.resize(a, (int(a.shape[1] * h / a.shape[0]), h))
    b = cv2.resize(b, (int(b.shape[1] * h / b.shape[0]), h))
    return np.hstack([a, b])


def _vstack(frames: list[np.ndarray]) -> np.ndarray:
    w = max(f.shape[1] for f in frames)
    resized = []
    for f in frames:
        h = int(f.shape[0] * w / f.shape[1])
        resized.append(cv2.resize(f, (w, h)))
    return np.vstack(resized)


def _write_mp4(path: Path, frames: list[np.ndarray], fps: float) -> None:
    if not frames:
        return
    h, w = frames[0].shape[:2]
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(str(path), fourcc, fps, (w, h))
    for frame in frames:
        if frame.shape[:2] != (h, w):
            frame = cv2.resize(frame, (w, h))
        writer.write(frame)
    writer.release()

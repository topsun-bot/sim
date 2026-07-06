from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

import typer

from replay.config import ReplayConfig, default_data_paths
from replay.control.replay_loop import run_replay
from replay.mcap.reader import inspect_mcap

app = typer.Typer(help="D1 MCAP physics replay (MuJoCo / Isaac Sim)")


@app.command()
def inspect(
    mcap_path: Path = typer.Argument(..., help="MCAP file path"),
    as_json: bool = typer.Option(False, "--json", help="Output JSON"),
) -> None:
    """Inspect MCAP structure and sample messages."""
    result = inspect_mcap(mcap_path)
    payload = {
        "mcap_path": result.mcap_path,
        "duration_sec": round(result.duration_sec, 3),
        "time_start_sec": result.time_start_sec,
        "time_end_sec": result.time_end_sec,
        "channels": [
            {
                "topic": c.topic,
                "schema": c.schema_name,
                "encoding": c.encoding,
                "count": c.message_count,
            }
            for c in result.channels
        ],
        "samples": result.samples,
    }
    if as_json:
        typer.echo(json.dumps(payload, indent=2, default=str))
    else:
        typer.echo(f"MCAP: {result.mcap_path}")
        typer.echo(f"Duration: {result.duration_sec:.3f}s")
        typer.echo("Channels:")
        for c in result.channels:
            typer.echo(f"  {c.topic}: {c.message_count} msgs ({c.schema_name}/{c.encoding})")
        typer.echo("Samples:")
        for topic, sample in result.samples.items():
            typer.echo(f"  {topic}: {json.dumps(sample, default=str)[:200]}")


@app.command()
def run(
    mcap: Optional[Path] = typer.Option(None, "--mcap", help="MCAP file"),
    meta: Optional[Path] = typer.Option(None, "--meta", help="Episode meta JSON"),
    backend: str = typer.Option("mujoco", "--backend", help="mujoco or isaac"),
    source: str = typer.Option("command", "--source", help="command, follower, or leader"),
    output: Path = typer.Option(Path("output"), "--output", help="Output directory"),
    latency_compensation_ms: float = typer.Option(
        0.0, "--latency-compensation-ms", help="Shift control earlier by N ms"
    ),
    no_video: bool = typer.Option(False, "--no-video", help="Skip video export"),
) -> None:
    """Run physics closed-loop replay."""
    if mcap is None:
        mcap, default_meta = default_data_paths()
        if meta is None:
            meta = default_meta

    if mcap is None or not mcap.is_file():
        typer.echo("Error: --mcap required or data/eda9cc2192f7.mcap must exist", err=True)
        raise typer.Exit(1)

    config = ReplayConfig(
        mcap_path=mcap,
        meta_path=meta,
        backend=backend,
        source=source,
        output_dir=output,
        latency_compensation_ms=latency_compensation_ms,
        write_video=not no_video,
    )

    result = run_replay(config)
    r = result.report
    typer.echo(f"Replay complete: {result.output_dir}")
    typer.echo(f"  sim_success={r.sim_success}  meta_result={r.meta_result}")
    typer.echo(f"  joint_rmse={r.joint_rmse_deg:.2f}°  max_error={r.max_joint_error_deg:.2f}°")
    typer.echo(f"  sim2real_match={r.sim2real_match}")


def main() -> None:
    app()


if __name__ == "__main__":
    main()

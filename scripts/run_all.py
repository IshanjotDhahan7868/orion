"""Run ORION pipeline stages in sequence.

Usage examples:

  python scripts/run_all.py
  python scripts/run_all.py --from-week 5 --to-week 7
  python scripts/run_all.py --from-week 6 --no-stop-on-error --print-commands
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class Stage:
    week: int
    name: str
    script: Path


STAGES = [
    Stage(week=4, name="event_dry_run", script=ROOT_DIR / "scripts" / "week4_dry_run.py"),
    Stage(week=5, name="propagation_dry_run", script=ROOT_DIR / "scripts" / "week5_dry_run.py"),
    Stage(week=6, name="market_check", script=ROOT_DIR / "scripts" / "week6_market_check.py"),
    Stage(week=7, name="export_signals", script=ROOT_DIR / "scripts" / "week7_export_signals.py"),
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run ORION weekly stages.")
    parser.add_argument("--from-week", type=int, default=4, help="First week to run (default: 4)")
    parser.add_argument("--to-week", type=int, default=7, help="Last week to run (default: 7)")
    parser.add_argument(
        "--stop-on-error",
        dest="stop_on_error",
        action="store_true",
        default=True,
        help="Stop immediately when a stage fails (default).",
    )
    parser.add_argument(
        "--no-stop-on-error",
        dest="stop_on_error",
        action="store_false",
        help="Continue remaining stages after a failure.",
    )
    parser.add_argument(
        "--print-commands",
        action="store_true",
        help="Print each command before execution.",
    )
    return parser.parse_args()


def validate_range(from_week: int, to_week: int) -> None:
    if from_week > to_week:
        raise ValueError(f"Invalid week range: from_week ({from_week}) > to_week ({to_week})")

    known_weeks = {stage.week for stage in STAGES}
    if from_week not in known_weeks or to_week not in known_weeks:
        wk = sorted(known_weeks)
        raise ValueError(f"Supported weeks are {wk}; got from_week={from_week}, to_week={to_week}")


def stage_env() -> dict[str, str]:
    env = os.environ.copy()
    root_parent = str(ROOT_DIR.parent)
    cur = env.get("PYTHONPATH", "")
    entries = [str(ROOT_DIR), root_parent]
    if cur:
        entries.append(cur)
    env["PYTHONPATH"] = os.pathsep.join(entries)
    return env


def run_stage(stage: Stage, env: dict[str, str], print_commands: bool) -> int:
    cmd = [sys.executable, str(stage.script)]
    if print_commands:
        print("$", " ".join(cmd), flush=True)
    print(f"\n=== Week {stage.week}: {stage.name} ===", flush=True)
    completed = subprocess.run(cmd, cwd=str(ROOT_DIR), env=env, check=False)
    return completed.returncode


def main() -> int:
    args = parse_args()

    try:
        validate_range(args.from_week, args.to_week)
    except ValueError as err:
        print(f"Error: {err}", file=sys.stderr)
        return 2

    selected = [s for s in STAGES if args.from_week <= s.week <= args.to_week]

    if not selected:
        print("No stages selected.")
        return 0

    env = stage_env()
    failures: list[tuple[Stage, int]] = []

    for stage in selected:
        code = run_stage(stage, env=env, print_commands=args.print_commands)
        if code != 0:
            failures.append((stage, code))
            print(f"Stage failed: week={stage.week} name={stage.name} exit_code={code}", file=sys.stderr)
            if args.stop_on_error:
                break

    if failures:
        print("\nPipeline finished with failures:", file=sys.stderr)
        for stage, code in failures:
            print(f"- week {stage.week} ({stage.name}) -> exit {code}", file=sys.stderr)
        return 1

    print("\nPipeline completed successfully.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

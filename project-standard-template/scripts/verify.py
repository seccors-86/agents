#!/usr/bin/env python3
"""Run configured project gates. Zero third-party dependencies."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / ".project" / "config.json"


def main() -> int:
    if not CONFIG.exists():
        print("[FAIL] .project/config.json not found")
        return 2

    try:
        config = json.loads(CONFIG.read_text(encoding="utf-8"))
    except Exception as exc:
        print(f"[FAIL] invalid config: {exc}")
        return 2

    entries = config.get("validation", {}).get("commands", [])
    stop_on_failure = bool(config.get("validation", {}).get("stop_on_failure", True))

    failures: list[str] = []
    skipped: list[str] = []
    executed = 0

    print("Project Development Standard — verify\n")

    for item in entries:
        name = str(item.get("name") or "unnamed")
        command = str(item.get("command") or "").strip()
        required = bool(item.get("required", False))

        if not command or command.startswith("<"):
            if required:
                print(f"[FAIL] {name}: required gate has no real command configured")
                failures.append(name)
                if stop_on_failure:
                    break
            else:
                print(f"[SKIP] {name}: not configured")
                skipped.append(name)
            continue

        print(f"[RUN ] {name}: {command}")
        completed = subprocess.run(command, cwd=ROOT, shell=True, check=False)
        executed += 1
        if completed.returncode == 0:
            print(f"[PASS] {name}\n")
        else:
            print(f"[FAIL] {name}: exit code {completed.returncode}\n")
            failures.append(name)
            if stop_on_failure:
                break

    print("Summary")
    print(f"  executed: {executed}")
    print(f"  skipped:  {len(skipped)}")
    print(f"  failed:   {len(failures)}")

    if failures:
        print("\nVERIFICATION: FAIL")
        return 1

    if executed == 0:
        print("\nVERIFICATION: NO GATES EXECUTED")
        print("Configure real commands before treating the project as verified.")
        return 3

    print("\nVERIFICATION: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

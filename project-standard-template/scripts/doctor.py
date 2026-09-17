#!/usr/bin/env python3
"""Project Development Standard environment check. Zero third-party dependencies."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / ".project" / "config.json"

CORE_FILES = [
    ROOT / "AGENTS.md",
    ROOT / "PROJECT.md",
    CONFIG,
    ROOT / ".project" / "state.md",
    ROOT / ".agents" / "skills" / "project-workflow" / "SKILL.md",
]


def line(status: str, message: str) -> None:
    print(f"[{status:<4}] {message}")


def command_version(command: str, args: list[str] | None = None) -> str | None:
    exe = shutil.which(command)
    if not exe:
        return None
    try:
        result = subprocess.run(
            [exe, *(args or ["--version"])],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=8,
            check=False,
        )
        text = (result.stdout or result.stderr).strip().splitlines()
        return text[0][:120] if text else exe
    except Exception:
        return exe


def main() -> int:
    failures = 0
    warnings = 0

    print("Project Development Standard — doctor\n")

    for path in CORE_FILES:
        if path.exists():
            line("PASS", str(path.relative_to(ROOT)))
        else:
            line("FAIL", f"missing {path.relative_to(ROOT)}")
            failures += 1

    if CONFIG.exists():
        try:
            data = json.loads(CONFIG.read_text(encoding="utf-8"))
            version = data.get("standard", {}).get("version", "unknown")
            line("PASS", f"config parses; standard version={version}")
            project_name = data.get("project", {}).get("name", "")
            if not project_name or project_name.startswith("<"):
                line("WARN", "project.name is still a template placeholder")
                warnings += 1

            commands = data.get("validation", {}).get("commands", [])
            active = [c for c in commands if c.get("command") and not str(c.get("command")).startswith("<")]
            if active:
                line("PASS", f"{len(active)} validation command(s) configured")
            else:
                line("WARN", "no real validation commands configured yet")
                warnings += 1
        except Exception as exc:
            line("FAIL", f"invalid .project/config.json: {exc}")
            failures += 1

    git_version = command_version("git")
    if git_version:
        line("PASS", f"git: {git_version}")
    else:
        line("FAIL", "git not found")
        failures += 1

    line("PASS", f"python: {sys.version.split()[0]}")

    for tool in ("opencode", "codex", "claude"):
        version = command_version(tool)
        if version:
            line("INFO", f"{tool}: {version}")
        else:
            line("INFO", f"{tool}: not installed/detected (optional)")

    print(f"\nResult: {failures} failure(s), {warnings} warning(s)")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())

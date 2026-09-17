#!/usr/bin/env python3
"""Per-project AI token/cost telemetry.

Zero third-party dependencies. Metrics only by default: prompts and responses are not persisted.
Supported adapters: OpenCode cumulative stats, Claude Code JSON output, Codex local rollouts.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import uuid
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / ".project" / "config.json"
TOKEN_KEYS = ("input", "output", "reasoning", "cache_read", "cache_write")


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def load_config() -> dict[str, Any]:
    if not CONFIG_PATH.exists():
        raise SystemExit("Missing .project/config.json")
    return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))


def usage_paths(config: dict[str, Any]) -> tuple[Path, Path, Path]:
    usage = config.get("usage", {})
    events = ROOT / usage.get("events_dir", ".project/usage/events")
    snapshots = ROOT / ".project" / "usage" / "snapshots"
    report = ROOT / usage.get("report_path", ".project/usage/USAGE.md")
    events.mkdir(parents=True, exist_ok=True)
    snapshots.mkdir(parents=True, exist_ok=True)
    report.parent.mkdir(parents=True, exist_ok=True)
    return events, snapshots, report


def as_int(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def as_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def normalized_tokens(data: dict[str, Any] | None) -> dict[str, int]:
    """Normalize common harness naming without assuming provider billing semantics."""
    data = data or {}
    cache = data.get("cache") if isinstance(data.get("cache"), dict) else {}
    return {
        "input": as_int(data.get("input", data.get("input_tokens"))),
        "output": as_int(data.get("output", data.get("output_tokens"))),
        "reasoning": as_int(data.get("reasoning", data.get("reasoning_tokens"))),
        "cache_read": as_int(
            data.get(
                "cache_read",
                data.get("cache_read_tokens", data.get("cache_read_input_tokens", cache.get("read", 0))),
            )
        ),
        "cache_write": as_int(
            data.get(
                "cache_write",
                data.get(
                    "cache_write_tokens",
                    data.get("cache_creation_input_tokens", data.get("cache_write_input_tokens", cache.get("write", 0))),
                ),
            )
        ),
    }


def token_total(tokens: dict[str, int]) -> int:
    return sum(as_int(tokens.get(key)) for key in TOKEN_KEYS)


def empty_tokens() -> dict[str, int]:
    return {key: 0 for key in TOKEN_KEYS}


def add_tokens(target: dict[str, int], source: dict[str, int]) -> None:
    for key in TOKEN_KEYS:
        target[key] += as_int(source.get(key))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def costs_for_mode(reported: float | None, billing_mode: str) -> tuple[float | None, float | None]:
    if reported is None:
        return None, None
    if billing_mode == "api":
        return reported, reported
    if billing_mode == "subscription":
        return None, reported
    return None, None


def command_add(args: argparse.Namespace, config: dict[str, Any]) -> int:
    events, _, _ = usage_paths(config)
    event_id = args.event_id or str(uuid.uuid4())
    path = events / f"{event_id}.json"
    if path.exists():
        print(f"[SKIP] event already exists: {event_id}")
        return 0

    payload = {
        "schema_version": 1,
        "kind": "event",
        "event_id": event_id,
        "recorded_at": now_iso(),
        "harness": args.harness,
        "provider": args.provider,
        "model": args.model,
        "session_id": args.session_id,
        "billing_mode": args.billing_mode,
        "tokens": {
            "input": args.input,
            "output": args.output,
            "reasoning": args.reasoning,
            "cache_read": args.cache_read,
            "cache_write": args.cache_write,
        },
        "reported_cost_usd": args.reported_cost,
        "actual_cost_usd": args.actual_cost,
        "api_equivalent_cost_usd": args.api_equivalent_cost,
        "estimated": bool(args.estimated),
        "source": args.source,
    }
    write_json(path, payload)
    print(f"[PASS] recorded {path.relative_to(ROOT)}")
    return 0


def command_import_opencode(args: argparse.Namespace, config: dict[str, Any]) -> int:
    _, snapshots, _ = usage_paths(config)
    if not shutil.which("opencode"):
        print("[FAIL] opencode executable not found")
        return 2

    result = None
    for command in (
        ["opencode", "stats", "--project", "", "--json", "--cost"],
        ["opencode", "stats", "--project", "", "--json"],
    ):
        candidate = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, check=False)
        if candidate.returncode == 0 and candidate.stdout.strip():
            result = candidate
            break
    if result is None:
        print("[FAIL] could not obtain OpenCode JSON stats for current project")
        return 2

    try:
        raw = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        print(f"[FAIL] OpenCode output is not valid JSON: {exc}")
        return 2

    reported = as_float(raw.get("totalCost"))
    actual, equivalent = costs_for_mode(reported, args.billing_mode)
    models: list[dict[str, Any]] = []
    for key, item in (raw.get("modelUsage") or {}).items():
        if not isinstance(item, dict):
            continue
        provider, separator, model = str(key).partition("/")
        models.append(
            {
                "provider": provider if separator else None,
                "model": model if separator else provider,
                "tokens": normalized_tokens(item.get("tokens") if isinstance(item.get("tokens"), dict) else {}),
                "reported_cost_usd": as_float(item.get("cost")),
            }
        )

    snapshot = {
        "schema_version": 1,
        "kind": "snapshot",
        "snapshot_id": "opencode-current-project",
        "recorded_at": now_iso(),
        "harness": "opencode",
        "billing_mode": args.billing_mode,
        "sessions": as_int(raw.get("totalSessions")),
        "messages": as_int(raw.get("totalMessages")),
        "tokens": normalized_tokens(raw.get("totalTokens") if isinstance(raw.get("totalTokens"), dict) else {}),
        "reported_cost_usd": reported,
        "actual_cost_usd": actual,
        "api_equivalent_cost_usd": equivalent,
        "models": models,
        "source": "opencode stats --project current",
    }
    write_json(snapshots / "opencode.json", snapshot)
    print(f"[PASS] OpenCode snapshot: {token_total(snapshot['tokens']):,} token operations")
    return 0


def command_import_claude(args: argparse.Namespace, config: dict[str, Any]) -> int:
    events, _, _ = usage_paths(config)
    source = Path(args.file).expanduser().resolve()
    raw_bytes = source.read_bytes()
    digest = hashlib.sha256(raw_bytes).hexdigest()
    event_id = f"claude-{digest[:24]}"
    path = events / f"{event_id}.json"
    if path.exists():
        print(f"[SKIP] already imported: {event_id}")
        return 0

    raw = json.loads(raw_bytes.decode("utf-8"))
    usage = raw.get("usage") if isinstance(raw.get("usage"), dict) else {}
    reported = as_float(raw.get("total_cost_usd", raw.get("cost_usd")))
    actual, equivalent = costs_for_mode(reported, args.billing_mode)
    payload = {
        "schema_version": 1,
        "kind": "event",
        "event_id": event_id,
        "recorded_at": now_iso(),
        "harness": "claude-code",
        "provider": "anthropic",
        "model": raw.get("model"),
        "session_id": raw.get("session_id"),
        "billing_mode": args.billing_mode,
        "tokens": normalized_tokens(usage),
        "reported_cost_usd": reported,
        "actual_cost_usd": actual,
        "api_equivalent_cost_usd": equivalent,
        "estimated": False,
        "source": source.name,
    }
    write_json(path, payload)
    print(f"[PASS] imported {path.relative_to(ROOT)}")
    return 0


def is_project_cwd(value: Any) -> bool:
    if not value:
        return False
    try:
        project = os.path.normcase(str(ROOT.resolve()))
        candidate = os.path.normcase(str(Path(str(value)).expanduser().resolve()))
        return os.path.commonpath([project, candidate]) == project
    except (OSError, ValueError):
        return False


def parse_codex_rollout(path: Path) -> dict[str, Any] | None:
    cwd: str | None = None
    provider: str | None = None
    model: str | None = None
    session_id: str | None = None
    last_usage: dict[str, Any] | None = None

    try:
        with path.open("r", encoding="utf-8", errors="replace") as handle:
            for raw_line in handle:
                try:
                    line = json.loads(raw_line)
                except json.JSONDecodeError:
                    continue
                kind = line.get("type")
                payload = line.get("payload") if isinstance(line.get("payload"), dict) else {}

                if kind == "session_meta":
                    meta = payload.get("meta") if isinstance(payload.get("meta"), dict) else payload
                    cwd = meta.get("cwd") or cwd
                    provider = meta.get("model_provider") or meta.get("modelProvider") or provider
                    session_id = meta.get("session_id") or meta.get("id") or session_id
                elif kind == "turn_context":
                    cwd = payload.get("cwd") or cwd
                    model = payload.get("model") or model
                    provider = payload.get("model_provider") or payload.get("modelProvider") or provider
                elif kind == "event_msg" and payload.get("type") == "token_count":
                    info = payload.get("info") if isinstance(payload.get("info"), dict) else {}
                    usage = info.get("total_token_usage") or info.get("totalTokenUsage")
                    if isinstance(usage, dict):
                        last_usage = usage
    except OSError:
        return None

    if not is_project_cwd(cwd) or last_usage is None:
        return None

    raw_input = as_int(last_usage.get("input_tokens"))
    cache_read = as_int(last_usage.get("cached_input_tokens"))
    cache_write = as_int(last_usage.get("cache_write_input_tokens"))
    raw_output = as_int(last_usage.get("output_tokens"))
    reasoning = as_int(last_usage.get("reasoning_output_tokens"))

    # Codex reports cache as part of input and reasoning as part of output.
    # Store mutually exclusive normalized counters so aggregate totals do not double count.
    tokens = {
        "input": max(0, raw_input - cache_read - cache_write),
        "output": max(0, raw_output - reasoning),
        "reasoning": reasoning,
        "cache_read": cache_read,
        "cache_write": cache_write,
    }
    return {
        "session_id": str(session_id or path.stem),
        "provider": provider or "openai",
        "model": model or "unknown",
        "tokens": tokens,
        "mtime": path.stat().st_mtime,
    }


def command_import_codex(args: argparse.Namespace, config: dict[str, Any]) -> int:
    _, snapshots, _ = usage_paths(config)
    codex_home = Path(args.codex_home or os.environ.get("CODEX_HOME", Path.home() / ".codex")).expanduser()
    sessions_dir = codex_home / "sessions"
    if not sessions_dir.exists():
        print(f"[FAIL] Codex sessions directory not found: {sessions_dir}")
        return 2

    sessions: dict[str, dict[str, Any]] = {}
    scanned = 0
    for path in sessions_dir.rglob("*.jsonl"):
        scanned += 1
        parsed = parse_codex_rollout(path)
        if not parsed:
            continue
        previous = sessions.get(parsed["session_id"])
        if previous is None or token_total(parsed["tokens"]) > token_total(previous["tokens"]):
            sessions[parsed["session_id"]] = parsed

    total = empty_tokens()
    model_totals: dict[tuple[str, str], dict[str, int]] = defaultdict(empty_tokens)
    for item in sessions.values():
        add_tokens(total, item["tokens"])
        add_tokens(model_totals[(item["provider"], item["model"])], item["tokens"])

    models = [
        {"provider": provider, "model": model, "tokens": tokens, "reported_cost_usd": None}
        for (provider, model), tokens in sorted(model_totals.items())
    ]
    snapshot = {
        "schema_version": 1,
        "kind": "snapshot",
        "snapshot_id": "codex-local-project-rollouts",
        "recorded_at": now_iso(),
        "harness": "codex",
        "billing_mode": args.billing_mode,
        "sessions": len(sessions),
        "tokens": total,
        "reported_cost_usd": None,
        "actual_cost_usd": args.actual_cost,
        "api_equivalent_cost_usd": args.api_equivalent_cost,
        "models": models,
        "source": "local Codex rollout JSONL token_count events",
        "files_scanned": scanned,
    }
    write_json(snapshots / "codex.json", snapshot)
    print(
        f"[PASS] Codex snapshot: {len(sessions)} project session(s), "
        f"{token_total(total):,} normalized tokens; scanned {scanned} rollout file(s)"
    )
    if args.billing_mode == "subscription" and args.api_equivalent_cost is None:
        print("[INFO] subscription usage has no invented per-project dollar value; API equivalent remains unknown")
    return 0


def load_records(config: dict[str, Any]) -> tuple[list[dict[str, Any]], list[str]]:
    events_dir, snapshots_dir, _ = usage_paths(config)
    records: list[dict[str, Any]] = []
    warnings: list[str] = []
    snapshot_harnesses: set[str] = set()

    for path in sorted(snapshots_dir.glob("*.json")):
        try:
            record = json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:
            warnings.append(f"invalid snapshot ignored: {path.name} ({exc})")
            continue
        if record.get("kind") == "snapshot":
            records.append(record)
            snapshot_harnesses.add(str(record.get("harness") or path.stem))

    seen: set[str] = set()
    for path in sorted(events_dir.glob("*.json")):
        try:
            record = json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:
            warnings.append(f"invalid event ignored: {path.name} ({exc})")
            continue
        if record.get("kind") != "event":
            continue
        event_id = str(record.get("event_id") or path.stem)
        if event_id in seen:
            warnings.append(f"duplicate event ignored: {event_id}")
            continue
        seen.add(event_id)
        harness = str(record.get("harness") or "unknown")
        if harness in snapshot_harnesses:
            warnings.append(f"event {event_id} ignored because {harness} has a cumulative snapshot")
            continue
        records.append(record)
    return records, warnings


def aggregate(records: list[dict[str, Any]]) -> dict[str, Any]:
    def bucket() -> dict[str, Any]:
        return {
            "records": 0,
            "tokens": empty_tokens(),
            "reported_cost_usd": 0.0,
            "reported_cost_count": 0,
            "actual_cost_usd": 0.0,
            "actual_cost_count": 0,
            "api_equivalent_cost_usd": 0.0,
            "api_equivalent_cost_count": 0,
        }

    totals = bucket()
    by_harness: dict[str, dict[str, Any]] = defaultdict(bucket)
    by_model: dict[str, dict[str, Any]] = defaultdict(bucket)

    def add_record(target: dict[str, Any], tokens: dict[str, int], record: dict[str, Any]) -> None:
        target["records"] += 1
        add_tokens(target["tokens"], tokens)
        for key in ("reported_cost_usd", "actual_cost_usd", "api_equivalent_cost_usd"):
            value = as_float(record.get(key))
            if value is not None:
                target[key] += value
                target[key.replace("_usd", "_count")] += 1

    for record in records:
        tokens = normalized_tokens(record.get("tokens") if isinstance(record.get("tokens"), dict) else {})
        add_record(totals, tokens, record)
        add_record(by_harness[str(record.get("harness") or "unknown")], tokens, record)

        if isinstance(record.get("models"), list):
            for model_item in record["models"]:
                if not isinstance(model_item, dict):
                    continue
                key = "/".join(str(x) for x in (model_item.get("provider"), model_item.get("model")) if x) or "unknown"
                add_record(
                    by_model[key],
                    normalized_tokens(model_item.get("tokens") if isinstance(model_item.get("tokens"), dict) else {}),
                    model_item,
                )
        elif record.get("model"):
            key = "/".join(str(x) for x in (record.get("provider"), record.get("model")) if x)
            add_record(by_model[key], tokens, record)

    return {"totals": totals, "by_harness": dict(by_harness), "by_model": dict(by_model)}


def cost_text(bucket: dict[str, Any], key: str) -> str:
    count_key = key.replace("_usd", "_count")
    return f"${bucket[key]:,.4f}" if bucket.get(count_key, 0) else "—"


def make_report(agg: dict[str, Any], warnings: list[str]) -> str:
    total = agg["totals"]
    tokens = total["tokens"]
    lines = [
        "# AI Usage — Project Report",
        "",
        f"Generated: `{now_iso()}`",
        "",
        "> Métricas somente. Nenhum prompt/resposta é necessário para este relatório.",
        "",
        "## Totais",
        "",
        f"- **Tokens observados (categorias normalizadas): {token_total(tokens):,}**",
        f"- Input não-cache: {tokens['input']:,}",
        f"- Output não-reasoning: {tokens['output']:,}",
        f"- Reasoning: {tokens['reasoning']:,}",
        f"- Cache read: {tokens['cache_read']:,}",
        f"- Cache write/creation: {tokens['cache_write']:,}",
        f"- **Custo reportado:** {cost_text(total, 'reported_cost_usd')}",
        f"- **Custo real atribuído:** {cost_text(total, 'actual_cost_usd')}",
        f"- **Equivalente de API:** {cost_text(total, 'api_equivalent_cost_usd')}",
        "",
        "## Por harness",
        "",
        "| Harness | Tokens | Reportado | Real | Equiv. API |",
        "|---|---:|---:|---:|---:|",
    ]
    for harness, item in sorted(agg["by_harness"].items()):
        lines.append(
            f"| {harness} | {token_total(item['tokens']):,} | "
            f"{cost_text(item, 'reported_cost_usd')} | {cost_text(item, 'actual_cost_usd')} | "
            f"{cost_text(item, 'api_equivalent_cost_usd')} |"
        )

    if agg["by_model"]:
        lines += ["", "## Por modelo", "", "| Provider/model | Tokens | Custo reportado |", "|---|---:|---:|"]
        for model, item in sorted(agg["by_model"].items(), key=lambda row: token_total(row[1]["tokens"]), reverse=True):
            lines.append(f"| {model} | {token_total(item['tokens']):,} | {cost_text(item, 'reported_cost_usd')} |")

    if warnings:
        lines += ["", "## Avisos", ""] + [f"- {warning}" for warning in warnings]

    lines += [
        "",
        "## Como ler custos",
        "",
        "- **Reportado:** valor fornecido/calculado pelo harness/provider.",
        "- **Real:** cobrança metered/API que pôde ser atribuída a este projeto.",
        "- **Equiv. API:** comparação econômica; não significa cobrança real em uma assinatura.",
        "- `—` significa desconhecido, não zero.",
        "",
    ]
    return "\n".join(lines)


def command_report(args: argparse.Namespace, config: dict[str, Any]) -> int:
    _, _, report_path = usage_paths(config)
    records, warnings = load_records(config)
    agg = aggregate(records)
    report = make_report(agg, warnings)
    report_path.write_text(report, encoding="utf-8")
    print(json.dumps(agg, ensure_ascii=False, indent=2) if args.json else report)
    if not args.json:
        print(f"\n[PASS] wrote {report_path.relative_to(ROOT)}")
    return 0


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description="Per-project AI token/cost telemetry")
    commands = root.add_subparsers(dest="command", required=True)

    add = commands.add_parser("add", help="record one normalized usage event")
    add.add_argument("--harness", required=True)
    add.add_argument("--provider")
    add.add_argument("--model")
    add.add_argument("--session-id")
    add.add_argument("--event-id")
    add.add_argument("--billing-mode", choices=["api", "subscription", "unknown"], default="unknown")
    for name in TOKEN_KEYS:
        add.add_argument(f"--{name.replace('_', '-')}", dest=name, type=int, default=0)
    add.add_argument("--reported-cost", type=float)
    add.add_argument("--actual-cost", type=float)
    add.add_argument("--api-equivalent-cost", type=float)
    add.add_argument("--estimated", action="store_true")
    add.add_argument("--source")

    opencode = commands.add_parser("import-opencode", help="replace the cumulative OpenCode snapshot")
    opencode.add_argument("--billing-mode", choices=["api", "subscription", "unknown"], default="unknown")

    claude = commands.add_parser("import-claude-json", help="import a Claude Code --output-format json result")
    claude.add_argument("file")
    claude.add_argument("--billing-mode", choices=["api", "subscription", "unknown"], default="unknown")

    codex = commands.add_parser("import-codex", help="scan local Codex rollout metrics for this project")
    codex.add_argument("--codex-home")
    codex.add_argument("--billing-mode", choices=["api", "subscription", "unknown"], default="subscription")
    codex.add_argument("--actual-cost", type=float)
    codex.add_argument("--api-equivalent-cost", type=float)

    report = commands.add_parser("report", help="generate the consolidated project report")
    report.add_argument("--json", action="store_true")
    return root


def main() -> int:
    config = load_config()
    args = parser().parse_args()
    handlers = {
        "add": command_add,
        "import-opencode": command_import_opencode,
        "import-claude-json": command_import_claude,
        "import-codex": command_import_codex,
        "report": command_report,
    }
    return handlers[args.command](args, config)


if __name__ == "__main__":
    raise SystemExit(main())

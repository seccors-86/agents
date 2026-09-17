#!/usr/bin/env python3
"""Per-project AI usage ledger/report.

Zero third-party dependencies. Stores metrics only by default — no prompts or responses.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import uuid
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / ".project" / "config.json"


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def load_config() -> dict[str, Any]:
    if not CONFIG_PATH.exists():
        raise SystemExit("Missing .project/config.json")
    return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))


def usage_paths(config: dict[str, Any]) -> tuple[Path, Path, Path]:
    usage = config.get("usage", {})
    events = ROOT / usage.get("events_dir", ".project/usage/events")
    report = ROOT / usage.get("report_path", ".project/usage/USAGE.md")
    snapshots = ROOT / ".project" / "usage" / "snapshots"
    events.mkdir(parents=True, exist_ok=True)
    snapshots.mkdir(parents=True, exist_ok=True)
    report.parent.mkdir(parents=True, exist_ok=True)
    return events, snapshots, report


def n(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def f(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def normalize_tokens(data: dict[str, Any] | None) -> dict[str, int]:
    data = data or {}
    cache = data.get("cache") if isinstance(data.get("cache"), dict) else {}
    return {
        "input": n(data.get("input", data.get("input_tokens"))),
        "output": n(data.get("output", data.get("output_tokens"))),
        "reasoning": n(data.get("reasoning", data.get("reasoning_tokens"))),
        "cache_read": n(data.get("cache_read", data.get("cache_read_tokens", cache.get("read", 0)))),
        "cache_write": n(data.get("cache_write", data.get("cache_write_tokens", cache.get("write", 0)))),
    }


def token_sum(tokens: dict[str, int]) -> int:
    return sum(n(tokens.get(k)) for k in ("input", "output", "reasoning", "cache_read", "cache_write"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def cmd_add(args: argparse.Namespace, config: dict[str, Any]) -> int:
    events, _, _ = usage_paths(config)
    event_id = args.event_id or str(uuid.uuid4())
    path = events / f"{event_id}.json"
    if path.exists():
        print(f"[SKIP] event already exists: {event_id}")
        return 0

    tokens = {
        "input": args.input,
        "output": args.output,
        "reasoning": args.reasoning,
        "cache_read": args.cache_read,
        "cache_write": args.cache_write,
    }
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
        "tokens": tokens,
        "reported_cost_usd": args.reported_cost,
        "actual_cost_usd": args.actual_cost,
        "api_equivalent_cost_usd": args.api_equivalent_cost,
        "estimated": bool(args.estimated),
        "source": args.source,
        "notes": args.notes,
    }
    write_json(path, payload)
    print(f"[PASS] recorded {path.relative_to(ROOT)}")
    return 0


def parse_opencode_stats(raw: dict[str, Any], billing_mode: str) -> dict[str, Any]:
    tokens = normalize_tokens(raw.get("totalTokens") if isinstance(raw.get("totalTokens"), dict) else {})
    reported_cost = f(raw.get("totalCost"))

    if billing_mode == "api":
        actual_cost = reported_cost
        api_equivalent = reported_cost
    elif billing_mode == "subscription":
        actual_cost = None
        api_equivalent = reported_cost
    else:
        actual_cost = None
        api_equivalent = None

    models: list[dict[str, Any]] = []
    model_usage = raw.get("modelUsage")
    if isinstance(model_usage, dict):
        for model_key, usage in model_usage.items():
            if not isinstance(usage, dict):
                continue
            provider, _, model = str(model_key).partition("/")
            mtokens = normalize_tokens(usage.get("tokens") if isinstance(usage.get("tokens"), dict) else {})
            models.append({
                "provider": provider or None,
                "model": model or provider or str(model_key),
                "messages": n(usage.get("messages")),
                "tokens": mtokens,
                "reported_cost_usd": f(usage.get("cost")),
            })

    return {
        "schema_version": 1,
        "kind": "snapshot",
        "snapshot_id": f"opencode:{ROOT}",
        "recorded_at": now_iso(),
        "harness": "opencode",
        "project_path": str(ROOT),
        "billing_mode": billing_mode,
        "sessions": n(raw.get("totalSessions")),
        "messages": n(raw.get("totalMessages")),
        "tokens": tokens,
        "reported_cost_usd": reported_cost,
        "actual_cost_usd": actual_cost,
        "api_equivalent_cost_usd": api_equivalent,
        "models": models,
        "source": "opencode stats --project current --json --cost",
    }


def cmd_import_opencode(args: argparse.Namespace, config: dict[str, Any]) -> int:
    _, snapshots, _ = usage_paths(config)
    if not shutil.which("opencode"):
        print("[FAIL] opencode executable not found")
        return 2

    commands = [
        ["opencode", "stats", "--project", "", "--json", "--cost"],
        ["opencode", "stats", "--project", "", "--json"],
    ]
    result = None
    for command in commands:
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
        print(f"[FAIL] OpenCode output was not valid JSON: {exc}")
        return 2

    snapshot = parse_opencode_stats(raw, args.billing_mode)
    write_json(snapshots / "opencode.json", snapshot)
    write_json(snapshots / "opencode.raw.json", {"recorded_at": now_iso(), "data": raw})
    print(
        "[PASS] OpenCode snapshot updated — "
        f"{token_sum(snapshot['tokens']):,} token operations, "
        f"reported cost={snapshot.get('reported_cost_usd')}"
    )
    return 0


def cmd_import_claude_json(args: argparse.Namespace, config: dict[str, Any]) -> int:
    events, _, _ = usage_paths(config)
    source_path = Path(args.file).expanduser().resolve()
    raw_bytes = source_path.read_bytes()
    digest = hashlib.sha256(raw_bytes).hexdigest()
    event_id = f"claude-{digest[:24]}"
    event_path = events / f"{event_id}.json"
    if event_path.exists():
        print(f"[SKIP] this Claude result was already imported: {event_id}")
        return 0

    raw = json.loads(raw_bytes.decode("utf-8"))
    usage = raw.get("usage") if isinstance(raw.get("usage"), dict) else {}
    tokens = normalize_tokens(usage)

    reported_cost = f(raw.get("cost_usd", raw.get("total_cost_usd")))
    billing_mode = args.billing_mode
    actual_cost = reported_cost if billing_mode == "api" else None
    api_equivalent = reported_cost if billing_mode in ("api", "subscription") else None

    payload = {
        "schema_version": 1,
        "kind": "event",
        "event_id": event_id,
        "recorded_at": now_iso(),
        "harness": "claude-code",
        "provider": "anthropic",
        "model": raw.get("model"),
        "session_id": raw.get("session_id"),
        "billing_mode": billing_mode,
        "tokens": tokens,
        "reported_cost_usd": reported_cost,
        "actual_cost_usd": actual_cost,
        "api_equivalent_cost_usd": api_equivalent,
        "estimated": False,
        "source": str(source_path),
        "notes": "Imported from Claude Code JSON output; no prompt/response persisted here.",
    }
    write_json(event_path, payload)
    print(f"[PASS] imported {event_path.relative_to(ROOT)}")
    return 0


def load_records(config: dict[str, Any]) -> tuple[list[dict[str, Any]], list[str]]:
    events_dir, snapshots_dir, _ = usage_paths(config)
    records: list[dict[str, Any]] = []
    warnings: list[str] = []

    snapshots_by_harness: dict[str, dict[str, Any]] = {}
    for path in sorted(snapshots_dir.glob("*.json")):
        if path.name.endswith(".raw.json"):
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:
            warnings.append(f"ignored invalid snapshot {path.name}: {exc}")
            continue
        if data.get("kind") != "snapshot":
            continue
        harness = str(data.get("harness") or path.stem)
        snapshots_by_harness[harness] = data

    records.extend(snapshots_by_harness.values())

    seen_event_ids: set[str] = set()
    for path in sorted(events_dir.glob("*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:
            warnings.append(f"ignored invalid event {path.name}: {exc}")
            continue
        if data.get("kind") != "event":
            continue
        event_id = str(data.get("event_id") or path.stem)
        if event_id in seen_event_ids:
            warnings.append(f"duplicate event ignored: {event_id}")
            continue
        seen_event_ids.add(event_id)

        harness = str(data.get("harness") or "unknown")
        if harness in snapshots_by_harness:
            warnings.append(
                f"event {event_id} ignored because harness '{harness}' already has a cumulative snapshot"
            )
            continue
        records.append(data)

    return records, warnings


def aggregate(records: list[dict[str, Any]]) -> dict[str, Any]:
    totals = {
        "tokens": {"input": 0, "output": 0, "reasoning": 0, "cache_read": 0, "cache_write": 0},
        "reported_cost_usd": 0.0,
        "actual_cost_usd": 0.0,
        "api_equivalent_cost_usd": 0.0,
        "reported_cost_records": 0,
        "actual_cost_records": 0,
        "api_equivalent_records": 0,
    }
    by_harness: dict[str, dict[str, Any]] = defaultdict(lambda: {
        "records": 0,
        "tokens": {"input": 0, "output": 0, "reasoning": 0, "cache_read": 0, "cache_write": 0},
        "reported_cost_usd": 0.0,
        "actual_cost_usd": 0.0,
        "api_equivalent_cost_usd": 0.0,
    })
    models: dict[str, dict[str, Any]] = defaultdict(lambda: {
        "tokens": {"input": 0, "output": 0, "reasoning": 0, "cache_read": 0, "cache_write": 0},
        "reported_cost_usd": 0.0,
    })

    for record in records:
        tokens = normalize_tokens(record.get("tokens") if isinstance(record.get("tokens"), dict) else {})
        for key, value in tokens.items():
            totals["tokens"][key] += value

        harness = str(record.get("harness") or "unknown")
        h = by_harness[harness]
        h["records"] += 1
        for key, value in tokens.items():
            h["tokens"][key] += value

        for cost_key, count_key in (
            ("reported_cost_usd", "reported_cost_records"),
            ("actual_cost_usd", "actual_cost_records"),
            ("api_equivalent_cost_usd", "api_equivalent_records"),
        ):
            value = f(record.get(cost_key))
            if value is not None:
                totals[cost_key] += value
                totals[count_key] += 1
                h[cost_key] += value

        if isinstance(record.get("models"), list):
            for item in record["models"]:
                if not isinstance(item, dict):
                    continue
                key = "/".join(str(x) for x in (item.get("provider"), item.get("model")) if x) or "unknown"
                mt = normalize_tokens(item.get("tokens") if isinstance(item.get("tokens"), dict) else {})
                for token_key, value in mt.items():
                    models[key]["tokens"][token_key] += value
                rc = f(item.get("reported_cost_usd"))
                if rc is not None:
                    models[key]["reported_cost_usd"] += rc
        elif record.get("model"):
            key = "/".join(str(x) for x in (record.get("provider"), record.get("model")) if x)
            for token_key, value in tokens.items():
                models[key]["tokens"][token_key] += value
            rc = f(record.get("reported_cost_usd"))
            if rc is not None:
                models[key]["reported_cost_usd"] += rc

    return {"totals": totals, "by_harness": dict(by_harness), "models": dict(models)}


def money(value: float) -> str:
    return f"${value:,.4f}"


def make_report(agg: dict[str, Any], warnings: list[str]) -> str:
    totals = agg["totals"]
    tokens = totals["tokens"]
    total_ops = token_sum(tokens)

    lines = [
        "# AI Usage — Project Report",
        "",
        f"Generated: `{now_iso()}`",
        "",
        "> Este relatório contém métricas, não prompts/respostas. Valores de assinatura e API não são tratados como equivalentes sem identificação explícita.",
        "",
        "## Totais",
        "",
        f"- **Token operations observadas:** {total_ops:,}",
        f"- Input: {tokens['input']:,}",
        f"- Output: {tokens['output']:,}",
        f"- Reasoning: {tokens['reasoning']:,}",
        f"- Cache read: {tokens['cache_read']:,}",
        f"- Cache write: {tokens['cache_write']:,}",
    ]

    if totals["reported_cost_records"]:
        lines.append(f"- **Custo reportado pelos harnesses:** {money(totals['reported_cost_usd'])}")
    else:
        lines.append("- **Custo reportado pelos harnesses:** indisponível")

    if totals["actual_cost_records"]:
        lines.append(f"- **Custo real atribuído ao projeto:** {money(totals['actual_cost_usd'])}")
    else:
        lines.append("- **Custo real atribuído ao projeto:** não determinado")

    if totals["api_equivalent_records"]:
        lines.append(
            f"- **Custo equivalente de API:** {money(totals['api_equivalent_cost_usd'])} "
            "(não significa cobrança real quando o uso é por assinatura)"
        )
    else:
        lines.append("- **Custo equivalente de API:** não determinado")

    lines += [
        "",
        "## Por harness",
        "",
        "| Harness | Registros | Tokens | Custo reportado | Custo real | Equiv. API |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for harness, item in sorted(agg["by_harness"].items()):
        lines.append(
            f"| {harness} | {item['records']} | {token_sum(item['tokens']):,} | "
            f"{money(item['reported_cost_usd'])} | {money(item['actual_cost_usd'])} | "
            f"{money(item['api_equivalent_cost_usd'])} |"
        )

    if agg["models"]:
        lines += [
            "",
            "## Por modelo",
            "",
            "| Provider/model | Tokens | Custo reportado |",
            "|---|---:|---:|",
        ]
        for model, item in sorted(
            agg["models"].items(), key=lambda kv: token_sum(kv[1]["tokens"]), reverse=True
        ):
            lines.append(
                f"| {model} | {token_sum(item['tokens']):,} | {money(item['reported_cost_usd'])} |"
            )

    if warnings:
        lines += ["", "## Avisos", ""]
        lines.extend(f"- {warning}" for warning in warnings)

    lines += [
        "",
        "## Interpretação",
        "",
        "- **Custo reportado:** valor calculado/fornecido pelo harness/provider.",
        "- **Custo real:** valor que pôde ser atribuído como cobrança metered/API.",
        "- **Equiv. API:** quanto aquele uso representa a preços de API quando essa equivalência é conhecida.",
        "- Em planos por assinatura, custo real por projeto pode não ser separável; não inventamos rateio.",
        "",
    ]
    return "\n".join(lines)


def cmd_report(args: argparse.Namespace, config: dict[str, Any]) -> int:
    _, _, report_path = usage_paths(config)
    records, warnings = load_records(config)
    agg = aggregate(records)
    report = make_report(agg, warnings)
    report_path.write_text(report, encoding="utf-8")
    if args.json:
        print(json.dumps(agg, ensure_ascii=False, indent=2))
    else:
        print(report)
        print(f"\n[PASS] wrote {report_path.relative_to(ROOT)}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Per-project AI token/cost telemetry")
    sub = parser.add_subparsers(dest="command", required=True)

    add = sub.add_parser("add", help="add one normalized usage event")
    add.add_argument("--harness", required=True)
    add.add_argument("--provider")
    add.add_argument("--model")
    add.add_argument("--session-id")
    add.add_argument("--event-id")
    add.add_argument("--billing-mode", choices=["api", "subscription", "unknown"], default="unknown")
    add.add_argument("--input", type=int, default=0)
    add.add_argument("--output", type=int, default=0)
    add.add_argument("--reasoning", type=int, default=0)
    add.add_argument("--cache-read", type=int, default=0)
    add.add_argument("--cache-write", type=int, default=0)
    add.add_argument("--reported-cost", type=float)
    add.add_argument("--actual-cost", type=float)
    add.add_argument("--api-equivalent-cost", type=float)
    add.add_argument("--estimated", action="store_true")
    add.add_argument("--source")
    add.add_argument("--notes")

    oc = sub.add_parser("import-opencode", help="replace cumulative OpenCode snapshot for this project")
    oc.add_argument("--billing-mode", choices=["api", "subscription", "unknown"], default="unknown")

    cj = sub.add_parser("import-claude-json", help="import one Claude Code --output-format json result")
    cj.add_argument("file")
    cj.add_argument("--billing-mode", choices=["api", "subscription", "unknown"], default="unknown")

    report = sub.add_parser("report", help="generate project usage report")
    report.add_argument("--json", action="store_true")

    return parser


def main() -> int:
    config = load_config()
    args = build_parser().parse_args()
    if args.command == "add":
        return cmd_add(args, config)
    if args.command == "import-opencode":
        return cmd_import_opencode(args, config)
    if args.command == "import-claude-json":
        return cmd_import_claude_json(args, config)
    if args.command == "report":
        return cmd_report(args, config)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())

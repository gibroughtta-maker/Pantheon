"""`pantheon` CLI — list-personas / debate / replay.

Lightweight on purpose: M0 supports the demo loop. M1+ adds `pack build`,
`pack audit`, `migrate`, `gateway status`, etc.
"""
from __future__ import annotations

import asyncio
import os
from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from pantheon import (
    BudgetGuard,
    MockGateway,
    OpenAICompatibleGateway,
    Pantheon,
    registry,
)
from pantheon.obs.replay import default_session_dir
from pantheon.types.events import (
    PhaseBoundaryEvent,
    SpeechEvent,
    SwapEvent,
    SystemEvent,
    VerdictEvent,
)

app = typer.Typer(no_args_is_help=True, add_completion=False)
console = Console()


def _build_gateway(name: str | None):
    if name == "mock" or name is None:
        return MockGateway()
    if name == "openclaw":
        base = os.environ.get("OPENCLAW_BASE_URL", "http://localhost:8080/v1")
        key = os.environ.get("OPENCLAW_API_KEY")
        return OpenAICompatibleGateway(base_url=base, api_key=key)
    raise typer.BadParameter(f"unknown gateway {name!r}")


@app.command("list-personas")
def list_personas() -> None:
    """List all personas registered in the current process."""
    table = Table(title="Pantheon — registered personas")
    table.add_column("id")
    table.add_column("display")
    table.add_column("school")
    table.add_column("primary model")
    for p in sorted(registry.all(), key=lambda x: x.id):
        table.add_row(p.id, p.display_name, p.spec.school, p.spec.model_preference.primary)
    console.print(table)


@app.command()
def debate(
    personas: list[str] = typer.Argument(..., help="Persona ids, e.g. confucius socrates naval"),
    question: str = typer.Option(..., "--question", "-q"),
    rounds: int = typer.Option(3, "--rounds", "-r"),
    gateway: str = typer.Option("mock", help="mock | openclaw"),
    budget_usd: float = typer.Option(5.0),
    seed: int = typer.Option(0),
) -> None:
    """Run a debate end-to-end and print the verdict."""

    async def _go():
        p = Pantheon.summon(
            personas,
            gateway=_build_gateway(gateway),
            budget=BudgetGuard(max_usd=budget_usd),
        )
        sess = p.debate(question, rounds=rounds, seed=seed)
        async for ev in sess.stream():
            _print_event(ev)
        v = await sess.verdict()
        console.print(Panel.fit(_format_verdict(v), title="Verdict", border_style="cyan"))
        console.print(f"[dim]debate_id={v.debate_id}  trace_id={v.trace_id}[/]")
        console.print(f"[dim]calls={v.model_calls}  cost=${v.cost.total_usd:.4f}[/]")

    asyncio.run(_go())


@app.command()
def replay(
    debate_id: str = typer.Argument(...),
    sessions_dir: Path = typer.Option(None),
) -> None:
    """Replay a previously recorded debate from its JSONL file."""
    sd = sessions_dir or default_session_dir()
    path = sd / f"{debate_id}.jsonl"
    if not path.exists():
        raise typer.BadParameter(f"no recording at {path}")
    console.print(f"Replaying [cyan]{debate_id}[/] from {path}")
    # The recording lets us reconstruct the original transcript directly:
    import json

    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        if row["event"] == "debate_event":
            t = row.get("type")
            if t == "speech":
                console.print(f"[bold]seat {row['seat']} | {row['persona_id']}[/] {row['text']}\n")
            elif t == "phase_boundary":
                console.print(f"[dim]── {row['from_phase']} → {row['to_phase']}[/]")
            elif t == "swap":
                console.print(f"[yellow]⚡ swap[/] seat {row['seat']}: {row['from_id']} → {row['to_id']}")
            elif t == "system":
                console.print(f"[magenta][{row['role']}][/] {row['message']}")
            elif t == "verdict":
                console.print(f"[green]Verdict marker[/] for debate {row['debate_id']}")
        elif row["event"] == "verdict":
            from pantheon.types.verdict import Verdict

            v = Verdict.model_validate(row["verdict"])
            console.print(Panel.fit(_format_verdict(v), title="Verdict (replayed)"))


def _print_event(ev) -> None:
    if isinstance(ev, SpeechEvent):
        console.print(
            f"[bold cyan]seat {ev.seat} | {ev.persona_id}[/] [dim]({ev.model_id})[/]\n{ev.text}\n"
        )
    elif isinstance(ev, PhaseBoundaryEvent):
        console.print(f"[dim]── {ev.from_phase} → {ev.to_phase}[/]")
    elif isinstance(ev, SwapEvent):
        console.print(f"[yellow]⚡ swap[/] seat {ev.seat}: {ev.from_id} → {ev.to_id}")
    elif isinstance(ev, SystemEvent):
        console.print(f"[magenta][{ev.role}][/] {ev.message}")
    elif isinstance(ev, VerdictEvent):
        console.print(f"[green]✓ verdict ready[/] (debate_id={ev.debate_id})")


def _format_verdict(v) -> str:
    lines = [f"[bold]Question:[/] {v.question}", ""]
    lines.append("[bold]Consensus:[/]")
    for c in v.consensus:
        lines.append(f"  • ({', '.join(c.supporters)}, w={c.weight:.2f}) {c.statement}")
    if v.minority_opinion:
        lines.append("\n[bold]Minority:[/]")
        for m in v.minority_opinion:
            lines.append(f"  • [{m.holder}] {m.statement}")
    if v.action_items:
        lines.append("\n[bold]Action items:[/]")
        for a in v.action_items:
            lines.append(f"  • {a.action}")
    lines.append(
        f"\n[dim]robustness={v.consensus_robustness}  no_consensus={v.no_consensus}  "
        f"unverified_quotes={v.quality.unverified_quote_count}[/]"
    )
    lines.append(f"\n[dim italic]{v.disclaimer}[/]")
    return "\n".join(lines)


# =====================================================================
# Subcommands: persona / calibration / corpus
# =====================================================================

persona_app = typer.Typer(no_args_is_help=True, help="Persona ops: calibrate, ingest-corpus.")
calibration_app = typer.Typer(no_args_is_help=True, help="Calibration ops: replay.")
corpus_app = typer.Typer(no_args_is_help=True, help="Corpus ops: fetch, verify.")
app.add_typer(persona_app, name="persona")
app.add_typer(calibration_app, name="calibration")
app.add_typer(corpus_app, name="corpus")


@persona_app.command("calibrate")
def persona_calibrate(
    persona_ids: list[str] = typer.Argument(..., help="One or more persona ids"),
    anchors: str = typer.Option(
        "",
        "--anchors",
        "-a",
        help="Comma-separated anchor persona ids; if empty, runs L2-only mode",
    ),
    judges: str = typer.Option(
        "",
        "--judges",
        "-j",
        help="Comma-separated judge model ids; required for L4 (else L2-only)",
    ),
    gateway: str = typer.Option("mock", help="mock | openclaw — judge gateway"),
    seed: int = typer.Option(0),
    write_back: bool = typer.Option(
        True, "--write-back/--no-write-back",
        help="Update persona.yaml in place with the new skills + audit metadata",
    ),
) -> None:
    """Run L2 + L4 calibration for one or more personas.

    L2 always runs. L4 runs only if both --anchors and --judges are non-empty.
    Dimensions where |L2 − L4| > sigma_threshold get flagged in
    `manual_review/<persona>.md` for human resolution.
    """
    from pantheon import Model
    from pantheon.calibration.audit import write_calibration_metadata, write_manual_review_stub
    from pantheon.calibration.runner import run_calibration

    gw = _build_gateway(gateway)
    anchor_ids = [a.strip() for a in anchors.split(",") if a.strip()]
    judge_ids = [j.strip() for j in judges.split(",") if j.strip()]
    judge_models = [Model(id=j, gateway=gw) for j in judge_ids] if judge_ids else []

    async def _go() -> None:
        anchor_personas = [registry.get(a) for a in anchor_ids] if anchor_ids else []
        for pid in persona_ids:
            target = registry.get(pid)
            console.print(f"[cyan]Calibrating[/] {pid} "
                          f"(anchors={anchor_ids or '∅'}, judges={judge_ids or '∅ → L2-only'})")
            res = await run_calibration(
                target,
                anchor_personas=anchor_personas,
                judges=judge_models,
                seed=seed,
            )
            tbl = Table(title=f"Calibration result — {pid} (run {res.run_id})")
            tbl.add_column("dimension")
            tbl.add_column("L2", justify="right")
            tbl.add_column("L4", justify="right")
            tbl.add_column("σ", justify="right")
            tbl.add_column("final", justify="right")
            tbl.add_column("flag")
            for dim, final in res.final.items():
                l2 = res.l2.by_dimension[dim].score
                l4 = res.l4.by_dimension[dim].score if res.l4 else None
                sigma = res.sigma[dim]
                flag = "⚠ MANUAL REVIEW NEEDED" if dim in res.flags else ""
                tbl.add_row(
                    dim,
                    f"{l2:.3f}",
                    f"{l4:.3f}" if l4 is not None else "—",
                    f"{sigma:.3f}",
                    f"{final:.3f}",
                    flag,
                )
            console.print(tbl)
            console.print(f"[dim]recording: {res.recording_path}[/]")

            if write_back:
                # Find the persona.yaml on disk; we don't have a back-pointer
                # so we search common locations.
                candidate = _locate_persona_yaml(pid)
                if candidate:
                    write_calibration_metadata(candidate, res, apply_flagged=False)
                    console.print(f"[green]✓ wrote skills + audit.calibration to {candidate}[/]")
                else:
                    console.print(
                        f"[yellow]⚠ no persona.yaml found for {pid}; skipping write-back[/]"
                    )
            if res.flags:
                stub = Path("manual_review") / f"{pid}.md"
                write_manual_review_stub(stub, res)
                console.print(f"[yellow]⚠ wrote manual review stub: {stub}[/]")

    asyncio.run(_go())


def _locate_persona_yaml(persona_id: str) -> Path | None:
    """Best-effort search for a persona's YAML in development."""
    candidates: list[Path] = []
    here = Path(__file__).resolve()
    # Walk up to the package root, then look for personas dirs.
    for parent in [here.parents[3], here.parents[4]] if len(here.parents) >= 5 else []:
        for p in parent.rglob(f"{persona_id}/persona.yaml"):
            candidates.append(p)
    return candidates[0] if candidates else None


@calibration_app.command("replay")
def calibration_replay(
    run_id: str = typer.Argument(...),
    runs_dir: Path = typer.Option(None, "--runs-dir"),
) -> None:
    """Replay a calibration run from its JSONL recording. Read-only — prints
    the events; no LLM calls are made."""
    import json
    rd = runs_dir or (default_session_dir().parent / "calibration")
    path = rd / f"{run_id}.jsonl"
    if not path.exists():
        raise typer.BadParameter(f"no calibration recording at {path}")
    console.print(f"Replaying calibration [cyan]{run_id}[/] from {path}")
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        ev = row.get("event")
        if ev == "calibration_open":
            console.print(f"[dim]opened[/] target={row.get('target')} "
                          f"anchors={row.get('anchors')} judges={row.get('judges')}")
        elif ev == "calibration_l2":
            console.print(f"[bold]L2[/] {row.get('l2')}")
        elif ev == "calibration_l4":
            console.print(f"[bold]L4[/] {row.get('l4')}")
        elif ev == "calibration_close":
            console.print(f"[bold green]final[/] {row.get('final')}")
            if row.get("flags"):
                console.print(f"[yellow]flags[/] {row['flags']}")


@corpus_app.command("fetch")
def corpus_fetch(
    persona_ids: list[str] = typer.Argument(..., help="Persona ids whose corpus to fetch"),
    only: str = typer.Option("", "--only",
                              help="Only fetch this manifest source id (e.g. web_nt)"),
    cache_dir: Path = typer.Option(None, "--cache-dir",
                                    help="Override cache root (default ~/.pantheon/corpus)"),
    mirror: str = typer.Option("", "--mirror",
                                help="Optional mirror URL prefix for restricted regions"),
    skip_verify: bool = typer.Option(False, "--skip-verify",
                                      help="Skip sha256 verification (useful while bootstrapping)"),
) -> None:
    """Download the public-domain corpus referenced by each persona's
    `corpus/manifest.yaml` to a per-user cache. Verifies sha256 unless
    skipped. Uses pantheon's own httpx-based gateway pattern (timeout +
    exponential backoff)."""
    import asyncio as _asyncio
    import hashlib
    import yaml as _yaml
    import httpx

    cache_root = cache_dir or (Path.home() / ".pantheon" / "corpus")
    cache_root.mkdir(parents=True, exist_ok=True)

    async def _fetch_one(client: httpx.AsyncClient, url: str, dest: Path) -> int:
        backoffs = [1, 2, 4, 8]
        for i, b in enumerate(backoffs + [0]):
            try:
                r = await client.get(url, follow_redirects=True, timeout=60)
                r.raise_for_status()
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_bytes(r.content)
                return len(r.content)
            except httpx.HTTPError as e:
                if i == len(backoffs):
                    raise
                console.print(f"  [yellow]retry in {b}s after {e}[/]")
                await _asyncio.sleep(b)
        return 0

    async def _go() -> None:
        async with httpx.AsyncClient() as client:
            for pid in persona_ids:
                # Find the persona's corpus manifest.
                yaml_path = _locate_persona_yaml(pid)
                if not yaml_path:
                    console.print(f"[red]✗ {pid}: no persona.yaml found[/]")
                    continue
                manifest_path = yaml_path.parent / "corpus" / "manifest.yaml"
                if not manifest_path.exists():
                    console.print(f"[yellow]⚠ {pid}: no corpus/manifest.yaml[/]")
                    continue
                manifest = _yaml.safe_load(manifest_path.read_text(encoding="utf-8")) or {}
                target_dir = cache_root / pid
                console.print(f"[cyan]→[/] {pid} → {target_dir}")
                for entry in manifest.get("sources", []):
                    sid = entry.get("id") or entry.get("path", "<unnamed>")
                    if only and sid != only:
                        continue
                    upstream = entry.get("upstream") or []
                    rel_path = entry.get("path")
                    expected_sha = entry.get("sha256") or ""
                    if not upstream or not rel_path:
                        console.print(f"  [dim]skip {sid}: incomplete manifest entry[/]")
                        continue
                    dest = target_dir / rel_path
                    if dest.exists() and not skip_verify and expected_sha:
                        actual = hashlib.sha256(dest.read_bytes()).hexdigest()
                        if actual == expected_sha:
                            console.print(f"  [green]✓[/] {sid}: cached + verified")
                            continue
                    last_err: Exception | None = None
                    for url in upstream:
                        if mirror:
                            url = mirror.rstrip("/") + "/" + url.split("://", 1)[-1].split("/", 1)[-1]
                        try:
                            n = await _fetch_one(client, url, dest)
                            console.print(f"  [green]↓[/] {sid}: {n} bytes from {url}")
                            if expected_sha and not skip_verify:
                                actual = hashlib.sha256(dest.read_bytes()).hexdigest()
                                if actual != expected_sha:
                                    dest.unlink()
                                    raise RuntimeError(
                                        f"sha256 mismatch for {sid}: "
                                        f"expected {expected_sha[:12]}, got {actual[:12]}"
                                    )
                            last_err = None
                            break
                        except Exception as e:  # noqa: BLE001
                            last_err = e
                            console.print(f"  [yellow]✗ try next mirror after {e}[/]")
                    if last_err is not None:
                        console.print(f"  [red]✗ {sid}: all mirrors failed[/]")

    _asyncio.run(_go())


@corpus_app.command("verify")
def corpus_verify(
    persona_ids: list[str] = typer.Argument(...),
    cache_dir: Path = typer.Option(None, "--cache-dir"),
) -> None:
    """Verify cached corpus files match their manifest sha256."""
    import hashlib
    import yaml as _yaml

    cache_root = cache_dir or (Path.home() / ".pantheon" / "corpus")
    overall_ok = True
    for pid in persona_ids:
        yaml_path = _locate_persona_yaml(pid)
        if not yaml_path:
            console.print(f"[red]✗ {pid}: no persona.yaml[/]")
            overall_ok = False
            continue
        manifest_path = yaml_path.parent / "corpus" / "manifest.yaml"
        if not manifest_path.exists():
            console.print(f"[yellow]⚠ {pid}: no manifest[/]")
            continue
        manifest = _yaml.safe_load(manifest_path.read_text(encoding="utf-8")) or {}
        for entry in manifest.get("sources", []):
            sid = entry.get("id") or entry.get("path")
            expected = entry.get("sha256") or ""
            dest = cache_root / pid / (entry.get("path") or "")
            if not dest.exists():
                console.print(f"  [dim]· {pid}/{sid}: not cached[/]")
                continue
            if not expected:
                console.print(f"  [dim]· {pid}/{sid}: cached, no expected sha (skipped)[/]")
                continue
            actual = hashlib.sha256(dest.read_bytes()).hexdigest()
            if actual == expected:
                console.print(f"  [green]✓[/] {pid}/{sid}")
            else:
                console.print(f"  [red]✗[/] {pid}/{sid}: expected {expected[:12]}, got {actual[:12]}")
                overall_ok = False
    if not overall_ok:
        raise typer.Exit(1)


if __name__ == "__main__":
    app()

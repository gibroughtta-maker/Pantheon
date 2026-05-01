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


if __name__ == "__main__":
    app()

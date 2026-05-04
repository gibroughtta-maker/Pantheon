"""Tool dispatch for the Pantheon MCP server.

All tools are dispatched through ``handle(name, args, mgr)`` which
returns a JSON-serializable dict. The MCP server thin-wraps this into
``TextContent``.

Pulling the dispatch out of the server entry point makes the tools
unit-testable without binding to the MCP transport.
"""
from __future__ import annotations

import json
from typing import Any

from pantheon import registry
from pantheon.types.events import (
    PhaseBoundaryEvent,
    SpeechEvent,
    SwapEvent,
    SystemEvent,
    VerdictEvent,
)

from pantheon_mcp.sessions import SessionManager


# ============================================================================
# Tool schemas (JSON Schema fragments). Used by the MCP `list_tools` handler.
# ============================================================================

TOOL_SCHEMAS: list[dict[str, Any]] = [
    {
        "name": "summon",
        "description": (
            "Create a new pantheon session with the given persona ids. "
            "Returns a session_id you'll pass to debate / swap_persona / "
            "swap_model / get_verdict. Max 10 personas per session."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "personas": {
                    "type": "array",
                    "items": {"type": "string"},
                    "minItems": 1,
                    "maxItems": 10,
                },
            },
            "required": ["personas"],
        },
    },
    {
        "name": "debate",
        "description": (
            "Run a five-phase debate (opening → cross_exam → rebuttal → "
            "synthesis* → verdict). Streams the verdict back as a single "
            "JSON document. Recommended rounds: 3-5."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "session_id": {"type": "string"},
                "question": {"type": "string"},
                "rounds": {"type": "integer", "minimum": 1, "maximum": 10, "default": 3},
                "seed": {"type": "integer"},
            },
            "required": ["session_id", "question"],
        },
    },
    {
        "name": "swap_persona",
        "description": (
            "Queue a persona swap at a seat. Applied at the next phase "
            "boundary. The new persona inherits the seat's transcript and "
            "opens with an automatic handoff statement (relay mode)."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "session_id": {"type": "string"},
                "seat": {"type": "integer", "minimum": 1, "maximum": 10},
                "to": {"type": "string"},
            },
            "required": ["session_id", "seat", "to"],
        },
    },
    {
        "name": "swap_model",
        "description": (
            "Queue a model swap at a seat. Persona and history are "
            "preserved; only the underlying LLM changes."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "session_id": {"type": "string"},
                "seat": {"type": "integer", "minimum": 1, "maximum": 10},
                "to": {"type": "string"},
            },
            "required": ["session_id", "seat", "to"],
        },
    },
    {
        "name": "get_verdict",
        "description": (
            "Fetch the verdict for a session that has finished debating. "
            "Raises if debate() has not been called or has not completed."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {"session_id": {"type": "string"}},
            "required": ["session_id"],
        },
    },
    {
        "name": "cast_divination",
        "description": (
            "Run a divination (iching/tarot/runes/astrology/ziwei). "
            "Available from M4 onwards; currently returns 'not yet implemented'."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "method": {
                    "type": "string",
                    "enum": ["iching", "tarot", "runes", "astrology", "ziwei"],
                },
                "question": {"type": "string"},
                "seed": {"type": "integer"},
            },
            "required": ["method", "question"],
        },
    },
    {
        "name": "list_personas",
        "description": (
            "List all registered personas. Filterable by school. "
            "Returns id, display name, school, primary model preference."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "filter": {
                    "type": "object",
                    "properties": {"school": {"type": "string"}},
                },
            },
        },
    },
    {
        "name": "audit_persona",
        "description": (
            "Return the audit metadata declared in a persona's YAML "
            "(reviewers, cultural_sensitivity_score, known_biases, "
            "calibration history). Read-only."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {"persona_id": {"type": "string"}},
            "required": ["persona_id"],
        },
    },
]


# ============================================================================
# Dispatch
# ============================================================================

async def handle(name: str, args: dict[str, Any], mgr: SessionManager) -> dict[str, Any]:
    """Dispatch a tool call. Returns a JSON-serializable result dict."""
    if name == "summon":
        sid = mgr.summon(args["personas"])
        rec = mgr.get(sid)
        return {
            "session_id": sid,
            "agents": [
                {"seat": a.seat, "persona": a.persona.id, "model": a.model.id}
                for a in rec.pantheon.agents
            ],
        }

    if name == "debate":
        sid = args["session_id"]
        question = args["question"]
        rounds = int(args.get("rounds", 3))
        seed = args.get("seed")
        sess = mgr.start_debate(sid, question, rounds=rounds, seed=seed)
        events_summary: list[dict[str, Any]] = []
        async for ev in sess.stream():
            if isinstance(ev, SpeechEvent):
                events_summary.append({
                    "type": "speech",
                    "seat": ev.seat,
                    "persona": ev.persona_id,
                    "phase": ev.phase,
                    "text": ev.text[:600],
                })
            elif isinstance(ev, PhaseBoundaryEvent):
                events_summary.append({
                    "type": "phase_boundary",
                    "from": ev.from_phase,
                    "to": ev.to_phase,
                })
            elif isinstance(ev, SwapEvent):
                events_summary.append({
                    "type": "swap",
                    "seat": ev.seat,
                    "kind": ev.kind,
                    "from": ev.from_id,
                    "to": ev.to_id,
                })
            elif isinstance(ev, SystemEvent):
                events_summary.append({
                    "type": "system",
                    "role": ev.role,
                    "message": ev.message[:400],
                })
            elif isinstance(ev, VerdictEvent):
                events_summary.append({
                    "type": "verdict_marker",
                    "debate_id": ev.debate_id,
                })
        v = await sess.verdict()
        return {
            "session_id": sid,
            "debate_id": v.debate_id,
            "verdict": json.loads(v.model_dump_json()),
            "events": events_summary,
        }

    if name == "swap_persona":
        mgr.queue_swap_persona(args["session_id"], int(args["seat"]), args["to"])
        return {"queued": True, "seat": args["seat"], "to": args["to"]}

    if name == "swap_model":
        mgr.queue_swap_model(args["session_id"], int(args["seat"]), args["to"])
        return {"queued": True, "seat": args["seat"], "to": args["to"]}

    if name == "get_verdict":
        rec = mgr.get(args["session_id"])
        if rec.debate is None:
            raise ValueError("no debate running for this session")
        v = await rec.debate.verdict()
        return json.loads(v.model_dump_json())

    if name == "cast_divination":
        return {
            "implemented": False,
            "message": (
                "cast_divination is scheduled for M4 (pantheon-divination). "
                "It will require explicit `import pantheon_divination` + "
                "`accept_disclaimer()` in the host process."
            ),
            "method": args.get("method"),
        }

    if name == "list_personas":
        flt = (args.get("filter") or {})
        school = flt.get("school")
        out = []
        for p in registry.all():
            if school and p.spec.school != school:
                continue
            out.append({
                "id": p.id,
                "display": p.display_name,
                "school": p.spec.school,
                "primary_model": p.spec.model_preference.primary,
                "skills": p.spec.skills,
            })
        return {"personas": sorted(out, key=lambda x: x["id"])}

    if name == "audit_persona":
        p = registry.get(args["persona_id"])
        return {
            "persona_id": p.id,
            "audit": json.loads(p.spec.audit.model_dump_json()),
            "known_biases": p.spec.audit.known_biases,
        }

    raise ValueError(f"unknown tool: {name!r}")

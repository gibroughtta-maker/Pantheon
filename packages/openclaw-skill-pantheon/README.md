# @openclaw/skill-pantheon

OpenClaw skill manifest for the Pantheon multi-agent debate framework.
Registering this skill with OpenClaw exposes a `/pantheon` slash command
that lets a user summon a pantheon of personas, debate a question, and
return a verdict — all routed through OpenClaw's existing multi-LLM
gateway and budget tracking.

## Install

```bash
openclaw skills install @openclaw/skill-pantheon
```

This will:

1. `pip install pantheon-mcp` (the MCP server that backs the skill)
2. Register `skill.json` with the local OpenClaw daemon
3. Wire the `/pantheon` command in your OpenClaw UI

## How it works

The skill is a thin wrapper. When the user types `/pantheon`, OpenClaw:

1. Calls the MCP server's `list_personas` tool to populate the persona
   multiselect
2. Submits the form by calling `summon` then `debate`
3. Renders the resulting `Verdict` (consensus / minority / action items /
   quality metrics) inline

The MCP server itself, all sessions, and all recordings live entirely
under your OpenClaw process — no external SaaS.

## Environment

The skill forwards these environment variables from OpenClaw to the
MCP server:

| Variable | Purpose |
|---|---|
| `PANTHEON_GATEWAY` | `mock` (safe default) or `openclaw` |
| `OPENCLAW_BASE_URL` | Required when `PANTHEON_GATEWAY=openclaw` |
| `OPENCLAW_API_KEY` | Same |
| `OPENCLAW_PROJECT` | Optional project tag for budget routing |
| `PANTHEON_SESSIONS_DIR` | Where to land debate JSONL recordings |
| `PANTHEON_OTEL_ENDPOINT` | Optional OTel exporter |
| `PANTHEON_REGION` | Set to `cn` to refuse founders pack loading |

## License

MIT.

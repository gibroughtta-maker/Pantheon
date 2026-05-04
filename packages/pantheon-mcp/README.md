# pantheon-mcp

MCP server for the [Pantheon](https://github.com/gibroughtta-maker/Pantheon)
multi-agent debate framework. Lets any MCP-aware client (Claude Desktop,
Cursor, Cline, Claude Code) summon a pantheon of personas and run a
five-phase debate over a question with a single tool call.

## Install

```bash
pip install pantheon-mcp
# or, via uv:
uvx pantheon-mcp
```

## Configure your MCP client

Add to your client's MCP config (e.g. `~/Library/Application Support/Claude/claude_desktop_config.json`):

```jsonc
{
  "mcpServers": {
    "pantheon": {
      "command": "uvx",
      "args": ["pantheon-mcp"],
      "env": {
        "PANTHEON_GATEWAY": "openclaw",
        "OPENCLAW_BASE_URL": "https://your-openclaw/v1",
        "OPENCLAW_API_KEY": "..."
      }
    }
  }
}
```

If `PANTHEON_GATEWAY` is unset or `mock`, the server uses `MockGateway`
(deterministic; no LLM calls, no costs) — useful for trying the protocol
out before plugging in a real gateway.

## Tools

Per the v0.3 plan §2.2, this server exposes 8 tools:

| Tool | Purpose |
|---|---|
| `summon`           | Create a pantheon session with N personas (≤ 10) |
| `debate`           | Run a debate; returns the verdict |
| `swap_persona`     | Change the persona at a seat (queue-based; relay mode) |
| `swap_model`       | Change the model at a seat (persona + history preserved) |
| `get_verdict`      | Fetch the verdict for a finished session |
| `cast_divination`  | (M4 — placeholder; returns "not yet implemented") |
| `list_personas`    | Enumerate available personas, with school filter |
| `audit_persona`    | Run cultural-sensitivity self-check on a persona |

State is held in-process; sessions are referenced by `session_id`.
Records of every debate land at `~/.pantheon/sessions/<debate_id>.jsonl`
(or `$PANTHEON_SESSIONS_DIR`).

## License

MIT.

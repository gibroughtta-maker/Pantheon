# MCP Server

`pantheon-mcp` is a stdio MCP server that exposes the SDK's debate
machinery as 8 tools, callable from any MCP client.

## Tools

| Tool | Returns | Use |
|---|---|---|
| `summon` | `{ session_id, agents }` | Build a pantheon |
| `debate` | `{ verdict, events }` | Run the 5-phase debate |
| `swap_persona` | `{ queued: true }` | Queue persona swap; applied at next phase boundary |
| `swap_model` | `{ queued: true }` | Queue model swap; persona+history preserved |
| `get_verdict` | `Verdict` | Fetch the verdict (e.g. after async streaming) |
| `list_personas` | `{ personas: [...] }` | Enumerate all registered personas (filterable by school) |
| `audit_persona` | `{ audit, known_biases }` | Read declared audit metadata for a persona |
| `cast_divination` | placeholder | M4 — opt-in pantheon-divination plugin |

## Configure your MCP client

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

If `PANTHEON_GATEWAY` is unset or `mock`, no real LLM calls are made and
the response uses the deterministic `MockGateway` — useful for trying
the protocol before wiring in a gateway.

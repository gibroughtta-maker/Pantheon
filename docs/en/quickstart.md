# Quickstart

## Install

```bash
pip install pantheon-debate
```

For the MCP server (so any MCP-aware client can use it):

```bash
pip install pantheon-mcp
# or no-install via uvx:
uvx pantheon-mcp
```

## Run a debate (Python SDK)

```python
import asyncio
from pantheon import Pantheon, MockGateway

async def main():
    p = Pantheon.summon(
        ["confucius", "socrates", "naval"],
        gateway=MockGateway(),  # zero-cost demo
    )
    sess = p.debate("Should I quit my job?", rounds=3, seed=42)
    async for ev in sess.stream():
        print(ev)
    v = await sess.verdict()
    print(v.consensus[0].statement)

asyncio.run(main())
```

## Run via CLI

```bash
pantheon list-personas
pantheon debate confucius socrates naval -q "Is moderation a virtue?"
pantheon replay <debate_id>
```

## Run via MCP

Add to your MCP client config (e.g. Claude Desktop):

```jsonc
{
  "mcpServers": {
    "pantheon": {
      "command": "uvx",
      "args": ["pantheon-mcp"]
    }
  }
}
```

Then in the client: "summon confucius and naval to debate whether I should
take the job offer". The 8 tools (`summon`, `debate`, `swap_persona`,
`swap_model`, `get_verdict`, `list_personas`, `audit_persona`,
`cast_divination`) are the contract — anything that speaks MCP can use
them.

## Plug in real models

Set `PANTHEON_GATEWAY=openclaw` and provide `OPENCLAW_BASE_URL` +
`OPENCLAW_API_KEY` to route through OpenClaw's multi-LLM gateway.
Or use `OpenClawGateway`, `NimGateway`, or `OpenAICompatibleGateway`
directly from the SDK.

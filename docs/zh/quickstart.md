# 快速开始

## 安装

```bash
pip install pantheon-debate
```

如果想让任意 MCP 客户端用上 Pantheon：

```bash
pip install pantheon-mcp
# 或不安装直接通过 uvx 跑：
uvx pantheon-mcp
```

## 跑一场辩论（Python SDK）

```python
import asyncio
from pantheon import Pantheon, MockGateway

async def main():
    p = Pantheon.summon(
        ["confucius", "socrates", "naval"],
        gateway=MockGateway(),  # 零成本 demo
    )
    sess = p.debate("我应该辞职吗？", rounds=3, seed=42)
    async for ev in sess.stream():
        print(ev)
    v = await sess.verdict()
    print(v.consensus[0].statement)

asyncio.run(main())
```

## CLI 使用

```bash
pantheon list-personas
pantheon debate confucius socrates naval -q "节制是美德还是缺陷?"
pantheon replay <debate_id>
```

## 通过 MCP

把下面这段加到你的 MCP 客户端配置（如 Claude Desktop）：

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

然后在客户端里："召唤孔子和纳瓦尔来辩论我应不应该接这份工作。"
8 个 tool（`summon` / `debate` / `swap_persona` / `swap_model` /
`get_verdict` / `list_personas` / `audit_persona` / `cast_divination`）
就是契约——任何会说 MCP 的客户端都能用。

## 接入真模型

设 `PANTHEON_GATEWAY=openclaw` 并提供 `OPENCLAW_BASE_URL` +
`OPENCLAW_API_KEY` 就能让 OpenClaw 多 LLM gateway 路由。也可以直接
用 SDK 里的 `OpenClawGateway` / `NimGateway` / `OpenAICompatibleGateway`。

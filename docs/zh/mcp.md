# MCP Server

`pantheon-mcp` 是个 stdio MCP server，把 SDK 的辩论引擎暴露成 8 个 tool，
任意 MCP 客户端都能调。

## Tools

| Tool | 返回 | 用途 |
|---|---|---|
| `summon` | `{ session_id, agents }` | 创建一个 pantheon 会话 |
| `debate` | `{ verdict, events }` | 跑五阶段辩论 |
| `swap_persona` | `{ queued: true }` | 入队人格切换；下一 phase 边界生效 |
| `swap_model` | `{ queued: true }` | 入队模型切换；persona 与 history 都保留 |
| `get_verdict` | `Verdict` | 取 verdict（流式异步消费后用） |
| `list_personas` | `{ personas: [...] }` | 列出所有已注册 personas（可按 school 过滤） |
| `audit_persona` | `{ audit, known_biases }` | 读取 persona YAML 中声明的 audit metadata |
| `cast_divination` | placeholder | 接 pantheon-divination；要先 accept_disclaimer |

## 配置 MCP 客户端

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

`PANTHEON_GATEWAY` 不设或为 `mock` 时不会调用真 LLM，使用确定性的
`MockGateway`——适合先把协议跑通、再接真 gateway。

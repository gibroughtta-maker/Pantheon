# 万神殿 Pantheon

> 多 agent 辩论框架——召唤神祇、先知、历史名人就任意议题展开 5 阶段辩论。
> 支持三种发行：OpenClaw 插件、MCP server、独立 Python SDK。

```python
from pantheon import Pantheon

p = Pantheon.summon(["confucius", "socrates", "naval"])
verdict = await p.debate("我应该辞职做独立开发者吗？").run()
print(verdict.consensus[0].statement)
```

## 为什么

大多数多 agent 框架把 agent 当作"任务执行 worker"。万神殿把它们当作
**有持续人格的辩论者**——孔子、苏格拉底、纳瓦尔真的在分歧、可追溯地
引用各自典籍、共同产出含「共识 / 少数意见 / 行动建议」三段的 verdict。

## 四个正交层

- **Agent**（席位）—— 有 transcript，最多 10 个
- **Persona**（面具）—— 无状态人格，可被任意 agent 戴
- **Model**（引擎）—— 无状态 LLM
- **Memory**（典籍+经验）—— corpus / episodic / working 三种存储

辩论中可换 persona 而保留席位 transcript（接棒模式）；可换 model 而保留
persona 与历史（同一个孔子换大脑）；可基于 JSONL 录制完全重放。

## 已交付

- ✅ M0 — 四层架构、5 阶段 FSM、queue swap、replay、BudgetGuard
- ✅ M1.5 — Skill 校准管线（L2 检索 + L4 BT 配对 + σ flag）+ pantheon-pack-founders
- ✅ M1 — Citation Verifier 接 corpus、真 Devil's Advocate、RateLimit、OpenClaw/NIM、SqliteEpisodic
- 🚧 M2 — pantheon-mcp（8 个 tool）+ 13 内置 personas + OpenClaw skill manifest + 此文档站

详见 [Architecture](architecture.md) 与
[仓库内 v0.3 完整方案](https://github.com/gibroughtta-maker/Pantheon/blob/main/docs/spec/plan.md)。

# 参考

## Persona YAML schema (v1.0)

见 [`pantheon.types.persona.PersonaSpec`](https://github.com/gibroughtta-maker/Pantheon/blob/main/packages/pantheon-core/src/pantheon/types/persona.py)。
具体例子在
[`packages/pantheon-core/personas/`](https://github.com/gibroughtta-maker/Pantheon/tree/main/packages/pantheon-core/personas)。

## Verdict schema (v1.0)

见 [`pantheon.types.verdict.Verdict`](https://github.com/gibroughtta-maker/Pantheon/blob/main/packages/pantheon-core/src/pantheon/types/verdict.py)。
所有字段 Pydantic 校验；`verdict.no_consensus=True` 是一等结果——
框架不会强行造一个假共识。

## 流式事件

| 事件 | 字段 |
|---|---|
| `SpeechEvent` | seat, persona_id, phase, text, model_id |
| `PhaseBoundaryEvent` | from_phase, to_phase |
| `SwapEvent` | seat, kind (persona/model/memory), from_id, to_id, handoff_statement |
| `SystemEvent` | role (moderator/oracle/auditor/framework), message |
| `VerdictEvent` | debate_id |

每个事件都带 `session_id` 和单调递增的 `seq`。

## Gateway

| Gateway | 何时用 |
|---|---|
| `MockGateway` | 测试、demo、replay 兜底 |
| `ReplayGateway` | 零成本重放某场录制的辩论 |
| `OpenAICompatibleGateway` | 通用；OpenAI / DeepSeek / vLLM 等 |
| `OpenClawGateway` | OpenClaw 多 LLM 路由 |
| `NimGateway` | NVIDIA NIM endpoint |

## Memory

| Store | 后端 | 生命周期 |
|---|---|---|
| `EmbeddedCorpusStore` | in-memory hybrid embedding + BM25 | 进程 |
| `NullCorpusStore` | 无 | n/a |
| `SqliteEpisodicStore` | SQLite | 永久（可清空） |
| `NullEpisodicStore` | 无 | n/a |
| `WorkingMemory` | 进程内 | 一场辩论 |

## 系统角色（不占席位）

- `Moderator` — phase 推进；soft-consensus 检测
- `Oracle` — 终裁 verdict；M0 启发式，M1+ 加 LLM pass
- `Auditor` — claim grounding，通过 corpus 检索
- `DevilsAdvocate` — 共识检测后的单轮 challenger

## Plan 链接

完整 v0.3 生产级方案带状态标记见
[`docs/spec/plan.md`](https://github.com/gibroughtta-maker/Pantheon/blob/main/docs/spec/plan.md)。

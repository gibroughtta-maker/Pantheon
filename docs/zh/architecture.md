# 架构

## 四个正交层

```
Agent  （席位 / 持续 transcript）
  ↓ wears
Persona（无状态人格面具）
  ↓ powered by
Model  （无状态 LLM 引擎）
  ↓ grounded in
Memory （corpus + episodic + working）
```

每一层都可独立替换——这是框架的招牌特性。

| 操作 | 改变 | 保留 |
|---|---|---|
| `agent.swap_persona(p)` | persona、system prompt、corpus、引文风格 | history、seat、model |
| `agent.swap_model(m)` | LLM、provider | persona、history、corpus |
| `agent.swap_memory(profile)` | episodic 视图 | persona、model、history |

Swap 是入队、phase 边界生效——不会在 phase 中途切换，避免流式辩论
里的竞态。

## 五阶段 FSM

```
CREATED → OPENING → CROSS_EXAM → REBUTTAL → SYNTHESIS* → VERDICT → CLOSED
                                            (loop ≤ 3)
```

每个 phase 都是可插拔的 `PhaseStrategy`。Moderator 在 synthesis 阶段
检测到「软共识」会自动召唤 Devil's Advocate——一个单轮 challenger，
说出"共识漏掉了什么"。

## 引文 grounding

每个 persona 的直接引语会被 Auditor 对照该 persona 的 corpus 校验。
verbatim 命中得「verified」，编造的引语进入 Verdict 的
`quality.unverified_quote_count`。

## Skill 校准

Skill 分数不再手填。校准管线包含：

- **L2** — 7 维 × 6 道原型题，对 corpus 检索打分（覆盖度）
- **L4** — 与锚点 persona 的 LLM-judge 配对淘汰赛，用 Bradley-Terry
  最大似然解析
- **融合** — 加权均；|L2 − L4| > 0.2 时该维度强制人工审（不静默平均）

详见 [校准](calibration.md)。

## 生产级原语

- **OpenTelemetry** — 每 phase / call / retrieval 都是 span
- **Replay** — 每场辩论一份 JSONL；`ReplayGateway` 让任意辩论零成本
  完全重放
- **BudgetGuard** — 调用前预算检查；不静默
- **RateLimiter** — 模型级 token bucket；超限阻塞而非报错
- **5 类故障降级路径** —— 单 persona 超时、gateway 429、gateway down、
  oracle fail、corpus retrieval fail，每一类都有测试覆盖

完整 spec 见仓库内的
[v0.3 plan](https://github.com/gibroughtta-maker/Pantheon/blob/main/docs/spec/plan.md)。

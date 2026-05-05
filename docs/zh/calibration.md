# 校准

Skill 分数不再手填。框架跑一套 **L2 + L4** 混合管线，让每个数字都能
追溯到一次校准 run。

## L2 — corpus 检索覆盖度

对每个 `(persona, dimension)` 对，runner 用该维度的 6 道原型题对 persona
的 corpus 做检索（通过 `EmbeddedCorpusStore`）。打分 = 平均 top-hit
相似度，按命中源的多样性加权。

无 corpus 的 persona 各维度都是 `L2 = 0`——这是正确的："这个 corpus
不覆盖这个维度"。

## L4 — 锚点配对

每个维度，目标 persona 与每个锚点 persona 跨所有 probes 配对。三个
评委（可配置 LLM）投票（A 胜 / B 胜 / 平）。投票通过 **Bradley-Terry**
最大似然解析（Zermelo 迭代，30 行纯 Python）转成隐式强度。强度线性映射到
锚点已知分数定义的 [0, 1] 区间。

## 融合 + 人工审

```
final = w_l2 · L2  +  w_l4 · L4         （默认 0.4, 0.6）
σ     = |L2 − L4|
flag  = σ > 0.2  →  manual_review/<persona>.md
```

L2 和 L4 分歧超过阈值时，框架**不会静默平均**，而是 flag 这一维度，
写一份 markdown stub 让人工裁决。决定记录在
`audit.calibration.manual_overrides`。

## 跑一遍

```bash
# 仅 L2（无 LLM 成本）：
pantheon persona calibrate confucius --gateway mock --no-write-back

# 完整混合（真评委）：
pantheon persona calibrate jesus muhammad buddha \
  --anchors confucius,socrates,naval \
  --judges claude-opus-4-7,gpt-4o,deepseek-chat \
  --gateway openclaw

# 重放已记录的 run（零成本）：
pantheon calibration replay <run_id>
```

每场校准都落到 `~/.pantheon/calibration/<run_id>.jsonl`。
同 seed + 同 scripted gateway → 字节级一致。

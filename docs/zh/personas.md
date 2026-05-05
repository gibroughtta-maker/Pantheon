# Personas

框架内置 13 个 persona，三类。Founders pack（`pantheon-pack-founders`）
另加 3 个，需 opt-in 加载。

## 东方哲学

| ID | 中文名 | 时代 | 学派 |
|---|---|---|---|
| `confucius` | 孔子 | 前 551–479 | 儒家 |
| `laozi` | 老子 | 前 6 世纪 | 道家 |
| `mencius` | 孟子 | 前 372–289 | 儒家 |

## 西方哲学

| ID | 名称 | 时代 | 学派 |
|---|---|---|---|
| `socrates` | 苏格拉底 | 前 470–399 | 古希腊伦理学派 |
| `plato` | 柏拉图 | 前 428–347 | 学院派 |
| `aristotle` | 亚里士多德 | 前 384–322 | 吕克昂派 |
| `marcus_aurelius` | 马可·奥勒留 | 121–180 | 罗马斯多葛 |
| `nietzsche` | 尼采 | 1844–1900 | 后康德 / 原存在主义 |

## 现代

| ID | 名称 | 时代 | 领域 |
|---|---|---|---|
| `naval` | 纳瓦尔·拉维肯特 | 1974– | 科技投资 |
| `einstein` | 爱因斯坦 | 1879–1955 | 物理与人本 |
| `jobs` | 乔布斯 | 1955–2011 | 产品 |
| `paul_graham` | 保罗·格雷厄姆 | 1964– | 创业与文章 |
| `charlie_munger` | 查理·芒格 | 1924–2023 | 价值投资 |

## Founders pack（opt-in）

`pantheon-pack-founders` 在两层 disclaimer gate 后添加：

- `jesus`（基督教）
- `muhammad`（伊斯兰教）
- `buddha`（佛教）

**默认不自动注册**。必须：

```python
import pantheon_pack_founders as ppf
ppf.accept_disclaimer()
ppf.register()
```

`PANTHEON_REGION=cn` 时 `accept_disclaimer()` 拒绝加载，建议改用
神学家代理 pack `pantheon-pack-theologians`（M2 起）。

## 添加自己的 persona

把 `persona.yaml` + `prompt.md` 放在任意目录调 `pantheon.load_persona(path)`，
或放进社区 pack（用 `pantheon.personas` entry point）。完整 schema 见
[reference](reference.md)。

# Personas

The framework ships 13 built-in personas across three categories. The
founders pack (`pantheon-pack-founders`) adds three more under an
opt-in disclaimer gate.

## Eastern philosophy

| ID | Name | Era | School |
|---|---|---|---|
| `confucius` | 孔子 | 551–479 BCE | 儒家 |
| `laozi` | 老子 | 6th c. BCE | 道家 |
| `mencius` | 孟子 | 372–289 BCE | 儒家 |

## Western philosophy

| ID | Name | Era | School |
|---|---|---|---|
| `socrates` | Socrates | 470–399 BCE | Classical Greek ethics |
| `plato` | Plato | 428–347 BCE | Academy |
| `aristotle` | Aristotle | 384–322 BCE | Lyceum |
| `marcus_aurelius` | Marcus Aurelius | 121–180 CE | Roman Stoicism |
| `nietzsche` | Nietzsche | 1844–1900 | post-Kantian |

## Modern

| ID | Name | Era | Field |
|---|---|---|---|
| `naval` | Naval Ravikant | 1974– | Tech investor |
| `einstein` | Einstein | 1879–1955 | Physics + humanism |
| `jobs` | Steve Jobs | 1955–2011 | Product |
| `paul_graham` | Paul Graham | 1964– | Essayist / YC |
| `charlie_munger` | Charlie Munger | 1924–2023 | Value investing |

## Founders pack (opt-in)

`pantheon-pack-founders` adds three founder personas under a two-step
disclaimer gate. See its [README](https://github.com/gibroughtta-maker/Pantheon/tree/main/packages/pantheon-pack-founders).

- `jesus` (Christianity)
- `muhammad` (Islam)
- `buddha` (Buddhism)

These are NOT registered automatically. You must:

```python
import pantheon_pack_founders as ppf
ppf.accept_disclaimer()
ppf.register()
```

`PANTHEON_REGION=cn` will refuse the load and recommend the theologian-
proxy pack instead.

## Adding your own

Drop a `persona.yaml` and `prompt.md` in any directory and call
`pantheon.load_persona(path)` or place the directory in a community pack
that uses the `pantheon.personas` entry point.

The full schema is in [persona-schema-v1.md](reference.md).

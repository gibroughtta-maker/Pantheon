# pantheon-bridges

Bridges from Pantheon debate events to:

- **Telegram** — push verdict + speeches to a chat / channel
- **Obsidian** — write a verdict markdown file to your vault
- **Discord** — webhook post of the verdict + per-phase summary

Each bridge implements the `EventSink` protocol and consumes the
streaming events from `Session.stream()`. They are best used through
the `pipe()` helper which wires the stream of events into one or more
sinks asynchronously.

## Install

```bash
pip install pantheon-bridges            # all bridges
pip install pantheon-bridges[telegram]  # extras for telegram
pip install pantheon-bridges[discord]   # extras for discord
```

## Usage

```python
from pantheon import Pantheon
from pantheon_bridges import pipe
from pantheon_bridges.obsidian import ObsidianSink
from pantheon_bridges.telegram import TelegramSink

p = Pantheon.summon(["confucius", "naval"])
sess = p.debate("Should I quit?")
await pipe(
    sess,
    sinks=[
        ObsidianSink(vault="~/Vault", folder="Pantheon"),
        TelegramSink(bot_token="...", chat_id="..."),
    ],
)
```

The Obsidian sink writes a markdown file the moment the verdict lands;
the Telegram sink streams speech events as they arrive (one message
per phase boundary).

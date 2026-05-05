# pantheon-pack-template

Starter template for community Pantheon persona packs.

## What's here

```
pantheon-pack-template/
├── pyproject.toml                 # rename `pantheon-pack-example` to your pack
├── README.md                      # this file (replace with your description)
├── AUDIT.md                       # three-reviewer panel scaffold
├── src/pantheon_pack_example/
│   ├── __init__.py                # provide_personas() entry-point hook
│   └── py.typed
├── personas/
│   └── sample_persona/
│       ├── persona.yaml           # full schema, one filled example
│       ├── prompt.md              # system prompt template
│       └── corpus/
│           └── manifest.yaml      # corpus-fetch-on-demand manifest
└── tests/
    └── test_pack.py               # entry-point + persona load smoke
```

## How to use

1. Clone or copy this directory to a new git repo.
2. Find-replace `pantheon-pack-example` → `pantheon-pack-yourname`
   (pyproject `name`, src dir, entry-point key, this README).
3. Find-replace `sample_persona` → your first persona id.
4. Fill in `personas/<your-persona>/persona.yaml`:
   - `id`, `display`, `era`, `school`
   - `personality.core_values` and `catchphrases`
   - `skills` — start with hand-filled or all 0.5; calibration is below
   - `audit.known_biases` — REQUIRED. Be honest about the persona's
     historical / cultural / interpretive limitations
5. Write `prompt.md` — the persona's system prompt.
6. (Optional) Fill `corpus/manifest.yaml` with public-domain upstream
   sources; users `pantheon corpus fetch <persona>` to materialize.
7. Run the audit gate:
   ```bash
   pantheon pack audit packages/pantheon-pack-yourname
   ```
   Address any prompt-injection / manifest / cultural-sensitivity flags.
8. Calibrate the persona's skill vector:
   ```bash
   pantheon persona calibrate <persona-id> \
       --anchors confucius,socrates,naval \
       --judges claude-opus-4-7,gpt-4o,deepseek-chat
   ```
9. Recruit your three reviewers (insider / academic / outside) and
   fill `AUDIT.md` with their scores. Do not publish until each
   reviewer has signed off and `cultural_sensitivity_score ≥ 0.85`.
10. Publish: `python -m build` then `twine upload dist/*`.

## Why packs are opt-in by default

Some packs (religious founders, contemporary politicians, controversial
figures) need explicit disclaimers and region restrictions. The template
wires this through `accept_disclaimer()` — your pack's `provide_personas()`
returns `[]` until the user calls it. Adapt the gate to your pack's
sensitivity (you can also leave it permanently open if your pack is fine
to auto-load).

## License

Code: MIT (or your choice — update pyproject.toml).
Persona definitions: CC-BY-SA 4.0 recommended for community-shareability.

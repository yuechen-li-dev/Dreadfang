# Dreadfang

Dreadfang is a strict, generator-based Python authoring surface for deterministic stateful control logic.

It is intentionally narrow: node modules author control flow with Dreadfang ops, the validator enforces a restricted subset, and the runtime executes those nodes in pure Python.

## Current surface (M18 checkpoint)

Dreadfang currently includes:

* `dreadfang.core`: typed ops, `Df` helper factories, `Df.Key(...)`, and message/condition primitives
* `dreadfang.validator`: restricted-subset validation (`ValidateSource(...)`, `ValidateFile(...)`)
* `dreadfang.runtime`: pure Python execution (`RunNode(...)`) and resumable in-memory sessions (`DfSession`)
* typed state keys with runtime type checks and dirty-key tracking
* explicit `Df.Act(...)` intent records plus optional actuator dispatch boundary
* Story adapter helpers in `dreadfang.adapters.story` (`Story.Line`, `Story.Say`, `Story.Option`, `Story.Choice`)

## Three-zone boundary model

1. **Restricted node modules**
   * validator-clean Dreadfang authoring code
   * no arbitrary imports, IO, or library side effects
2. **Runtime/wiring modules**
   * ordinary Python
   * load modules, build registries, create `DfSession`, inject messages
3. **Actuator modules**
   * ordinary Python boundary code
   * interpret recorded `Df.Act(...)` records and may perform side effects

The act stream in `DfRunResult.Acts` remains semantic truth even when no actuator is registered.

## Samples

See `samples/README.md` for a sample index and file boundary map.

Included sample areas:

* patrol/recover flow (`samples/PatrolRecover*`)
* utility + hysteresis/min-commit decisions (`samples/UtilityCommitment*`)
* text-adventure Story adapter flow (`samples/text_adventure/*`)

## Running tests

```bash
python -m pytest -q
```

## Text adventure sample status

The text adventure sample is currently exposed as runtime/test helpers, not as a packaged interactive CLI.

Use:

* `samples/text_adventure/StoryNodes.py` for restricted authored flow
* `samples/text_adventure/StoryRuntime.py` for ordinary Python runtime wiring/actuator helpers
* `tests/test_m17_story_adapter.py` for end-to-end run/resume behavior

## Current non-goals / limitations

* no lowering/backend pipeline yet
* no persistence/save-restore of live Python generator sessions
* no arbitrary Python inside restricted node modules
* no plugin framework
* no async event-loop scheduler

## Authoring guide

For detailed authoring rules and runtime boundary guidance, see `docs/authoring.md`.

## License

MIT.

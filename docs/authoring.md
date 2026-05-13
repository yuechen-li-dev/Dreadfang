# Dreadfang Authoring Guide (Current Boundary)

This guide documents Dreadfang **as it exists now** in this repository.

## 1) What Dreadfang is

Dreadfang is a restricted, generator-based Python authoring surface for control logic.

It is **not** general-purpose Python, not a plugin framework, and not a lowering/backend pipeline yet. The current scope is authoring + pure-Python execution of strict control scripts through `dreadfang.core`, `dreadfang.runtime`, and `dreadfang.validator`.

## 2) File boundary model

Dreadfang has three practical zones:

1. **Restricted node modules**
   * Contain authored node/scorer functions.
   * Must validate with `ValidateSource(...)` / `ValidateFile(...)`.
   * Example: `samples/PatrolRecoverNodes.py`, `samples/UtilityCommitmentNodes.py`.

2. **Runtime/wiring modules (ordinary Python)**
   * Build registries, construct context, run nodes, inspect results.
   * Not expected to pass restricted-subset validation.
   * Example: `samples/PatrolRecoverSample.py`, `samples/UtilityCommitmentSample.py`.

3. **Actuator modules (ordinary Python boundary code)**
   * Optional effect handlers for recorded acts.
   * May call wrappers/libraries/IO as needed.
   * Not expected to pass restricted-subset validation.

Keep node modules small and strict; keep runtime and actuator logic outside that subset.

## 3) Canonical node shape

```python
from dreadfang.core import Df, DfCtx, DfNode

def Root(ctx: DfCtx) -> DfNode:
    yield Df.Act("Line", "hello")
    yield Df.Wait(1)
    yield Df.Succeed()
```

Rules of thumb:

* Nodes take `DfCtx`.
* Nodes are generators yielding Dreadfang ops (`DfNode`).
* Yield Dreadfang ops only (e.g., `Df.Act`, `Df.Wait`, `Df.Push`, `Df.Decide`, `Df.Succeed`).
* Do not yield arbitrary raw values.

## 4) `yield from` vs `Push` / `Pop`

### Linear composition: `yield from`

Use `yield from Child(ctx)` when the child is just inline progression in the same frame.

```python
def Root(ctx):
    yield Df.Act("RootStart")
    yield from PatrolBeat(ctx)
    yield Df.Succeed()
```

### True stack semantics: `Push` / `Pop`

Use `Df.Push("Child")` to enter a named node via runtime registry; use `Df.Pop()` from that child to resume parent.

```python
def Parent(ctx):
    yield Df.Act("ParentStart")
    yield Df.Push("RecoverBeat")
    yield Df.Act("ParentResume")
    yield Df.Succeed()


def RecoverBeat(ctx):
    yield Df.Act("RecoverSweep")
    yield Df.Pop()
```

Guidance:

* Prefer `yield from` for simple linear factoring.
* Use `Push`/`Pop` for explicit suspended-parent stack behavior.
* Do not treat `yield from` as stack/registry dispatch.

## 5) State and context

`DfCtx` exposes:

* `ctx.State.Get(key, default)`
* `ctx.State.Set(key, value)`

Preferred authoring pattern in restricted node modules is typed keys declared at module top-level:

```python
Mode = Df.Key("Mode", str)
RecoverAttempts = Df.Key("RecoverAttempts", int)

ctx.State.Set(Mode, "patrol")
attempts = ctx.State.Get(RecoverAttempts, 0)
```

Typed keys enforce strict runtime type checks on both `Set` values and `Get` defaults. Raw string keys remain compatibility-only and are not the preferred authoring path.
* `ctx.Tick`
* `ctx.Mailbox`
* `ctx.LastMessage`

`Tick` advances from runtime ops like `Df.Wait(...)`. Keep state keys small, explicit, and stable (`"mode"`, `"signalIndex"`, etc.), as shown in sample nodes.

Waiting primitives:

* `Df.Wait(ticks)` waits fixed tick count.
* `Df.Await(name)` waits for mailbox message name.
* `Df.WaitUntil(condition)` waits for a symbolic state condition object.
* `Df.WaitUntil(...)` accepts condition objects built via `Df.StateEquals`, `Df.StateNotEquals`, `Df.StateAtLeast`, or `Df.StateAtMost`.
* Predicate callables/lambdas are not supported in `Df.WaitUntil`.
* False `WaitUntil` conditions return `Status="Waiting"` with a readable condition in `WaitingOn`.
* This is a boundary for one invocation only; no resumable session object exists yet.

Mailbox boundary:

* Runtime/wiring code may populate `ctx.Mailbox` with explicit `DfMessage` values (for example `Df.Message("Choice", "proud")`).
* Restricted node modules should wait using `yield Df.Await("Choice")`.
* On a successful await match, runtime consumes the first matching mailbox message and stores it in `ctx.LastMessage`.
* Restricted node modules may read `ctx.LastMessage`, `ctx.LastMessage.Name`, and `ctx.LastMessage.Payload`.
* Direct `ctx.Mailbox` reads/mutation are rejected by the validator for restricted node modules.
* If no message matches, runtime returns `Status="Waiting"` with `WaitingOn` set to the awaited message name. This is a terminal result for the invocation, not yet a resumable session system.

## 6) Actuation and actuators

Boundary law: **record first, dispatch second**.

* `Df.Act(name, payload)` records intent.
* Runtime appends it to `DfRunResult.Acts` first.
* If actuator handlers are registered, they run after the record is created.
* Unknown act names are still recorded and skipped when no handler exists.
* Handler exceptions propagate (not swallowed).

This keeps semantic truth in the run result record stream, while allowing optional impure boundary handlers.

## 7) Utility / commitment (`Option` + `Decide`)

Scorer functions are plain callables of shape `DfCtx -> float`.

* Keep scorers read-only/pure.
* Runtime clamps scores to `[0.0, 1.0]` before ranking.
* Build options with `Df.Option(label, scoreFn, target)`.
* Choose with `Df.Decide(..., hysteresis=..., min_commit_ticks=...)`.
* Decisions are recorded in `DfRunResult.Decisions`.
* Runtime commitment memory is keyed by stable logical frame identity (`Name#Instance`), not Python object identity.
* `yield from` stays in the same logical frame identity; explicit `Push`/`Pop` creates frame identity boundaries.

Tiny shape:

```python
def TrackScore(ctx):
    return float(ctx.State.Get("signal", 0.0))


def Root(ctx):
    yield Df.Decide(
        [
            Df.Option("Track", TrackScore, "TrackBeat"),
            Df.Option("Recover", RecoverScore, "RecoverBeat"),
        ],
        hysteresis=0.15,
        min_commit_ticks=2,
    )
```

## 8) Validation

API:

* `ValidateSource(sourceText: str, filename: str = "<memory>") -> DfValidationResult`
* `ValidateFile(path: str | Path) -> DfValidationResult`

Result shape:

* `DfValidationResult.IsValid: bool`
* `DfValidationResult.Diagnostics: tuple[DfValidationDiagnostic, ...]`
* each diagnostic has `Message`, `Line`, `Column`

Use validator on restricted node modules, not runtime/wiring/actuator modules.

Current restricted-subset bans include:

* imports
* classes
* decorators
* async/await features
* `try`/`except`, `raise`
* lambda
* comprehensions / generator expressions
* walrus (`:=`)
* arbitrary call targets outside allowed subset
* arbitrary `yield from` (only module-defined Dreadfang functions are allowed)

If validation fails, simplify node authoring shape instead of weakening the validator boundary.

## 9) Samples and split

Current sample split in `samples/`:

* `PatrolRecoverNodes.py`: restricted node module (validator target)
* `PatrolRecoverSample.py`: runtime wiring + registry setup
* `UtilityCommitmentNodes.py`: restricted node/scorer authoring
* `UtilityCommitmentSample.py`: runtime/config wrapper and run analysis

These samples show:

* linear composition via `yield from`
* stacked flow via `Push`/`Pop`
* `Act` boundary and intent emission
* utility/commitment via `Option` + `Decide`

## 10) Anti-patterns (do not)

* Do not put library/IO calls inside restricted node modules.
* Do not hide registration in decorators.
* Do not rely on import-time side effects.
* Do not `yield from` arbitrary Python generators.
* Do not mutate state from scorer functions.
* Do not treat actuator side effects as semantic truth (acts record is truth).
* Do not force runtime/wiring modules to conform to node-module validator rules.

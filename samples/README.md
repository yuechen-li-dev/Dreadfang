# Dreadfang Samples

This directory is organized to keep restricted authoring code separate from ordinary runtime code.

## Patrol / Recover sample

Demonstrates:

* sequential control with explicit state
* `yield from` composition
* stack-like control with `Df.Push(...)` / `Df.Pop(...)`
* explicit `Df.Act(...)` intent emission

Files:

* **Restricted node module**: `samples/PatrolRecoverNodes.py`
* **Ordinary runtime/wiring module**: `samples/PatrolRecoverSample.py`

## Utility / commitment sample

Demonstrates:

* scorer-based decisions with `Df.Option(...)` + `Df.Decide(...)`
* hysteresis and minimum-commit behavior
* stable frame identity behavior across execution

Files:

* **Restricted node module**: `samples/UtilityCommitmentNodes.py`
* **Ordinary runtime/wiring module**: `samples/UtilityCommitmentSample.py`

## Text adventure / Story sample

Demonstrates:

* thin story adapter helpers over core Dreadfang ops
* actuation output (`Story.Line`, `Story.Say`, `Story.Choice`)
* choice/resume flow using `Df.Await(...)` and `Df.Message(...)`

Files:

* **Restricted node module**: `samples/text_adventure/StoryNodes.py`
* **Ordinary runtime/wiring module**: `samples/text_adventure/StoryRuntime.py`

There is currently no packaged interactive CLI for the text-adventure sample in this repository; the sample is exercised through runtime helpers and tests.

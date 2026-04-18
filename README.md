# Dreadfang

Dreadfang is a restricted generator-based authoring surface for stateful control logic.

Its goal is not to be “Python, but with fewer features.”
Its goal is to make sequential, readable authoring possible without giving up explicit state, deterministic behavior, or future portability.

Dreadfang is meant to feel closer to **Dominatus-style authoring** than to ordinary framework-heavy Python.

## What Dreadfang is

Dreadfang is:

* a constrained Python authoring surface
* generator-based
* function-first
* explicit
* typed
* deterministic by design
* intended for stateful logic such as:

  * AI/control loops
  * reactive systems
  * narrative flow
  * other bounded progression/state-machine problems

A Dreadfang node should read like a small script, not like a framework object or a bag of callbacks.

## What Dreadfang is not

Dreadfang is **not**:

* general-purpose Python with a cool name
* a framework for arbitrary dynamic behavior
* a license to use Python magic because “it works”
* an excuse to hide control flow in decorators, globals, or reflection
* a giant runtime architecture
* a production lowering pipeline yet

For now, Dreadfang exists to prove the authoring surface first.

## Design principles

Dreadfang follows a few simple rules:

* Prefer the dull solution.
* Prefer explicit state over hidden state.
* Prefer readable sequential authoring over clever abstraction.
* Prefer typed data and obvious boundaries.
* Prefer deterministic behavior.
* Prefer a small control vocabulary over framework sprawl.
* Do not use a Python feature merely because it exists.

The intent is to keep Dreadfang code easy to review, easy to test, and hard to accidentally turn into a swamp.

## Naming convention

Dreadfang uses **CamelCase** for function names.

This is intentional.

Dreadfang is a constrained cross-language authoring surface, not ordinary general-purpose Python code, and its naming is meant to preserve interoperability with other runtimes and future generated backends rather than follow default Python style conventions.

## Current status

This repository is at the beginning.

Right now, the project is focused on:

* establishing the repo shape
* locking in authoring rules
* defining what Dreadfang nodes should look like
* building the smallest viable pure-Python runtime for those nodes

The first priority is to prove that the authoring surface is good.

The repository now includes an initial `dreadfang.core` surface with typed node/context/state primitives, core op dataclasses, and `Df` helper factories for authored nodes.

## Planned direction

The expected early path is:

1. define the node/op vocabulary
2. build a small pure-Python runtime
3. validate the restricted subset
4. pressure-test authoring ergonomics with tiny samples
5. only later decide what should become IR and what should remain surface syntax

So the immediate question is not “how do we lower this?”
The immediate question is “is this a good way to author stateful logic at all?”

## Repository rules

The `primer/` directory and `AGENTS.md` are load-bearing.

In particular:

* Dreadfang code uses a restricted Python subset
* function-first design is preferred
* dynamic magic is unwelcome
* side effects must stay visible
* readability beats convention theater
* if a feature makes lowering, review, or testing harder, it should probably not be used

## Intended shape

A Dreadfang node should eventually look like a small sequential control script:

* read context/state
* yield a bounded control operation
* continue clearly
* avoid hidden machinery

That is the center of gravity for the project.

## License

MIT.

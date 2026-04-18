document:
  name: python-primer
  format: toon
  version: 1

intent:
  summary:
    Define the narrow Python subset allowed in this repository.
    Reduce ambiguity, avoid dynamic foot-cannons, and keep code explicit, typed, testable, and easy to refactor.
  audience:
    primary:
      LLM authors
    secondary:
      human contributors
    additional:
      notebook users migrating exploratory code into maintainable repository code
  non_goals:
    - This is not a general Python tutorial.
    - This is not a defense of every common "Pythonic" habit.
    - This is not permission to use dynamic features just because the language allows them.
    - This is not an excuse to turn a notebook into a permanent software architecture.
    - This is not a license to replace explicit design with dynamic cleverness.

goal:
  headline:
    Use boring, explicit, typed Python that keeps data shape, control flow, side effects, and runtime behavior obvious.
  success_criteria:
    - Code is easy to review locally.
    - Refactors stay localized.
    - Public APIs are typed and understandable.
    - Unit tests are meaningful.
    - Stable logic can move cleanly from notebooks into normal modules.
    - Authors do not introduce dynamic cleverness unless clearly required.
    - The repository remains understandable without guessing what objects or dictionaries contain.

core_principles:
  - Prefer the dull solution.
  - Prefer explicit behavior over hidden behavior.
  - Prefer typed data over shape-shifting dictionaries.
  - Prefer local reasoning over runtime magic.
  - Prefer ordinary functions over architecture theater.
  - Prefer standard library tools over novelty dependencies.
  - Keep side effects visible.
  - Keep data shape visible.
  - Do not use a Python feature merely because it exists.
  - Do not make the codebase more dynamic at the cost of making it less trustworthy.
  - Do not compress code so aggressively that its behavior becomes harder to inspect.

must_do:
  - Target the modern Python version supported by the repository.
  - Use type hints for public functions, methods, and important module-level interfaces.
  - Keep data shape explicit.
  - Keep functions small, narrow, and unsurprising.
  - Write code whose failure modes are visible in tests.
  - Keep side effects visible at the call site or module boundary.
  - Follow existing repository-local patterns before introducing a new one.
  - Keep stable logic in normal modules, not trapped inside notebooks.
  - Prefer obvious correctness over clever compactness.
  - Keep data flow and control flow easy to inspect in one pass.
  - Normalize loose external data into explicit internal shapes early.
  - Make it easy for a reviewer to tell what a function consumes, returns, mutates, and depends on.

recommended:
  - Prefer functions first.
  - Prefer dataclasses for structured records with clear fields.
  - Prefer small modules with explicit responsibilities.
  - Prefer pathlib over ad hoc string path handling.
  - Prefer explicit imports.
  - Prefer standard library containers and utilities before reaching for dependencies.
  - Prefer clear return values over mutation-heavy calling conventions.
  - Prefer simple comprehensions only when they stay easy to read.
  - Prefer explicit configuration objects or arguments over hidden global settings.
  - Prefer tests that exercise behavior directly instead of depending on incidental side effects.
  - Prefer named variables when intermediate values improve readability.
  - Prefer ordinary loops and helper functions over dense one-liners.
  - Prefer explicit schemas, records, or typed containers over nested dict and list blobs.
  - Prefer small pure functions where practical.

not_recommended:
  - Classes that exist only as namespaces with self attached.
  - Inheritance-heavy design.
  - Broad untyped dict and list data flow through core logic.
  - Decorators that hide important control flow or side effects.
  - Clever one-liners that reduce readability.
  - Import-time work beyond simple constant definition.
  - Utility dumping-ground modules.
  - Ad hoc scripts that silently become production logic.
  - Stateful notebooks that depend on cell execution order.
  - Framework-like abstractions introduced before a real need exists.
  - Silent fallback behavior.
  - Reaching for pandas or other heavy tools when ordinary Python would be clearer.
  - Accumulating business logic inside lambdas, comprehensions, or chained expression soup.
  - Reusing dynamic JSON-shaped payloads deep into the application instead of normalizing them.
  - Naming that depends on cultural Python shorthand instead of plain meaning.

restricted:
  - Dynamic attribute injection is restricted.
  - Monkeypatching in normal application code is restricted.
  - Metaclasses are restricted.
  - Decorator stacks that hide behavior are restricted.
  - Runtime code generation and exec-style patterns are restricted.
  - Broad except blocks are restricted.
  - Bare except is banned.
  - Silent exception swallowing is banned.
  - Async is restricted unless the repository is already async-first in that area.
  - Hidden mutable module globals are restricted.
  - Import-time I/O, network calls, or registration side effects are restricted.
  - Any-heavy typing is restricted.
  - Novel dependencies without clear need are restricted.
  - Implicit registration systems are restricted.
  - Reflection-heavy dispatch is restricted.
  - Magic __getattr__, __setattr__, and similar behavior-hiding hooks are restricted outside narrow justified use.
  - Mutable default arguments are banned.

default_patterns:
  functions_first:
    headline:
      Python is function-first by default.
    rules:
      - Prefer plain functions for most behavior.
      - Use classes only when there is real state, lifecycle, or invariant management.
      - Do not create classes merely to mimic architecture from other languages.
      - Do not introduce manager, service, helper, or controller classes without a concrete need.
      - Do not wrap simple behavior in classes to look "structured."
    guidance:
      - In this repository, Python is primarily a language for explicit functions operating on typed data.
      - If a function plus a small typed record solves the problem cleanly, that is usually the correct answer.

  typing:
    headline:
      Public types should be explicit and useful.
    rules:
      - Type public functions and methods.
      - Keep parameter and return types clear.
      - Avoid Any unless it is truly unavoidable.
      - Prefer explicit structured types over vague containers.
      - Use TypedDict only when a dictionary-shaped boundary is genuinely required.
      - Do not leave important interfaces untyped because the code "still runs."
    guidance:
      - Type hints are not decoration.
      - Their job is to make shape, expectation, and intent visible before runtime.
      - Prefer Protocol for structural boundaries when behavior matters more than inheritance ancestry.

  dataclasses_and_validation:
    headline:
      Dataclasses should stay simple, but may validate real invariants.
    rules:
      - Prefer dataclasses for structured records with clear fields.
      - Use __post_init__ for small, direct invariant checks when validation is genuinely part of the type.
      - Do not turn dataclasses into mini-frameworks with hidden behavior.
      - Keep validation local, explicit, and easy to test.
    guidance:
      - A dataclass may protect a real invariant.
      - It should not become a magical lifecycle object.

  defaults_and_function_signatures:
    headline:
      Function defaults must not hide shared mutable state.
    rules:
      - Do not use mutable default arguments.
      - Use None and create a fresh value inside the function when a mutable default is needed.
      - Keep default behavior explicit and unsurprising.
    guidance:
      - Mutable defaults are a classic haunted-house bug.
      - If state should persist across calls, make that persistence explicit instead of smuggling it through a default.

  data_modeling:
    headline:
      Data shape must be obvious.
    rules:
      - Prefer dataclasses for structured records.
      - Prefer named fields over positional mystery tuples.
      - Avoid passing nested dict soup through core logic.
      - Normalize loose external data into typed shapes early.
      - Keep internal representations simpler than boundary payloads, not messier.
    guidance:
      - If reviewers must remember what arbitrary keys might exist in a dict, the design is too loose.
      - Unstructured input is acceptable at boundaries. It should not remain unstructured deep inside the system.

  exceptions:
    headline:
      Exceptions are allowed, but must remain disciplined.
    rules:
      - Use exceptions for actual exceptional failure, not normal branching.
      - Catch narrow exception types when possible.
      - Do not use bare except.
      - Do not swallow exceptions silently.
      - Do not hide failure behind logging alone.
      - Do not convert every ordinary branch into try/except control flow.
    guidance:
      - Python uses exceptions naturally, but that does not make broad or hidden exception handling acceptable.
      - Failure should still be honest and inspectable.

  side_effects_and_state:
    headline:
      Side effects should be visible and controlled.
    rules:
      - Avoid hidden mutable globals.
      - Avoid import-time work.
      - Pass configuration explicitly when practical.
      - Keep I/O, filesystem, network, and environment access near clear boundaries.
      - Do not let hidden state drive core logic.
      - Do not surprise callers with mutation that the API does not make obvious.
    guidance:
      - A reader should be able to tell whether a function computes, mutates, performs I/O, or touches environment state without detective work.

  decorators:
    headline:
      Decorators may simplify code, but may not hide behavior.
    rules:
      - Use simple, obvious decorators only.
      - Do not hide retries, caching, registration, I/O, mutation, or permission logic behind surprising decorator stacks.
      - If a decorator makes control flow harder to inspect, do not use it.
      - Do not use decorators to create mini-framework behavior in ordinary repository code.
    guidance:
      - A function should still look like what it does.
      - If the important behavior lives in the decorator stack instead of the function body, the design is too opaque.

  modules_and_imports:
    headline:
      Modules should have clear boundaries and predictable imports.
    rules:
      - Keep modules focused.
      - Import explicitly.
      - Do not create circular dependency tangles.
      - Do not turn one module into the repository junk drawer.
      - Keep import-time behavior minimal.
      - Separate boundary code from core logic when practical.
    guidance:
      - A module should have a reason to exist beyond "miscellaneous helpers."
      - If a module is becoming a storage closet, split it.
      - Keep package export surfaces intentional rather than accidental when __init__.py is used.

  dependencies:
    headline:
      Prefer boring dependencies.
    rules:
      - Reach for the standard library first.
      - Use repository-established dependencies before adding new ones.
      - Do not add a package for a problem already solved clearly by existing tools.
      - Heavy frameworks need strong justification.
      - Do not import a dependency just to save a few obvious lines.
    guidance:
      - Dependency cost is not just installation. It is also conceptual weight, ecosystem churn, and maintenance burden.

  notebooks:
    headline:
      Notebooks are for exploration, not permanent architecture.
    rules:
      - Keep exploratory cells small and explicit.
      - Move stable logic into .py modules.
      - Do not depend on hidden cell state.
      - Do not leave core business logic trapped in notebooks.
      - Treat notebooks as orchestration and experimentation layers, not the final home of maintainable code.
      - Prefer calling typed module functions from notebooks instead of embedding the logic directly in cells.
    guidance:
      - Notebook code is not exempt from discipline.
      - Once a workflow matters, it should graduate into normal modules that can be imported, tested, and reviewed.

  performance:
    headline:
      Optimize late and locally.
    rules:
      - Do not pre-emptively complicate code for theoretical speed.
      - Keep performance-sensitive work isolated.
      - Prefer the clear version first, then optimize with evidence.
      - Do not let vectorization theater or clever pipelines replace understandable logic without justification.
      - Do not rewrite whole modules around hypothetical bottlenecks.
    guidance:
      - Performance work should be surgical, not ideological.
      - The codebase should not become harder to understand in exchange for guesses.

  comprehensions_and_expressions:
    headline:
      Short expressions are fine. Puzzle code is not.
    rules:
      - Use list, dict, and set comprehensions when they remain short and obvious.
      - Avoid nested comprehensions with heavy filtering and transformation logic.
      - Break expression chains into named intermediate values when clarity improves.
      - Do not hide business logic inside lambdas or one-liners to save vertical space.
    guidance:
      - Brevity is useful until it starts acting like camouflage.

portability_rules:
  - Code should run consistently in the repository's supported Python environments.
  - Do not depend on interpreter quirks or environment-specific accidents.
  - Keep environment assumptions explicit.
  - Isolate platform-specific behavior behind narrow boundaries when necessary.
  - Do not assume notebook state, REPL history, or local machine layout is part of the runtime contract.

author_operating_rules:
  - First inspect nearby code and mirror established local patterns.
  - Do not introduce a second pattern for a problem the repository already solved.
  - Do not widen the repository subset during implementation.
  - Do not infer that a more dynamic Python feature is preferred just because it is available.
  - When multiple solutions are valid, choose the one with the clearest data shape.
  - When multiple solutions are valid, choose the one with the least hidden side effect.
  - When multiple solutions are valid, choose the one with the most obvious runtime behavior.
  - If a construct makes review harder, refactoring riskier, or tests less trustworthy, avoid it.
  - If unsure, choose the simpler and more explicit construct.
  - Do not import patterns from random online Python examples unless the repository already uses them.
  - Do not solve a local problem by increasing global dynamism.
  - Do not mistake "Pythonic" for "good fit for this repository."
  - Do not assume that a compact solution is a better solution.
  - Do not leave type and shape decisions implicit when they can be made explicit cheaply.

decision_rules:
  - Prefer code that is obviously correct over code that is merely idiomatic.
  - Prefer local clarity over reusable cleverness.
  - Prefer one boring pattern used consistently over several elegant patterns mixed together.
  - Prefer explicit data flow over hidden mutation.
  - Prefer code that fails loudly in tests over code that can be secretly wrong.
  - Prefer designs that make notebook logic easy to migrate into modules.
  - Prefer simple typed records over informal dictionary conventions.
  - If the clever solution and the boring solution are both valid, choose the boring solution.

examples:
  typing_examples:
    headline:
      Show typed public APIs, explicit return types, and avoidance of Any-heavy design.

  data_shape_examples:
    headline:
      Show dataclass and typed record usage contrasted with nested dict soup.

  function_first_examples:
    headline:
      Show plain function-centered design contrasted with unnecessary class wrappers.

  exception_examples:
    headline:
      Show disciplined exceptions contrasted with broad catches and silent failure.

  decorator_examples:
    headline:
      Show acceptable simple decorators contrasted with behavior-hiding decorator stacks.

  notebook_examples:
    headline:
      Show notebook orchestration calling normal modules instead of embedding core logic in cells.

review_checklist:
  ask_before_merging:
    - Is the public typing explicit and useful?
    - Is the data shape obvious?
    - Are side effects visible?
    - Are exceptions handled narrowly and honestly?
    - Does this follow existing repository patterns?
    - Did this change introduce unnecessary classes or dynamic behavior?
    - Would a future maintainer understand this without guessing what shape the data has?
    - Would the simplest valid version of this code look substantially different?
    - Can stable logic be tested outside the notebook or script that currently calls it?
    - Did this change make the repository more dynamic than it needed to be?
  reject_if:
    - The change introduces hidden state.
    - The change introduces hidden control flow.
    - The change introduces unnecessary abstraction.
    - The change relies on dynamic magic instead of explicit structure.
    - The change makes testing, review, or refactoring meaningfully harder.
    - The change keeps important logic inside notebook cells when it should live in modules.

closing:
  message:
    This repository uses a narrow Python subset on purpose.
    The goal is not to show how flexible Python can be.
    The goal is to produce typed, explicit, testable code that is easy to review and hard to accidentally turn into a swamp.

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Literal, Mapping

from dreadfang.core import Act, Clamp01, Decide, DfCtx, DfNode, DfOp, Fail, Option, Pop, Push, Succeed, Wait

RunStatus = Literal["Succeeded", "Failed", "Incomplete"]
DfNodeFactory = Callable[[DfCtx], DfNode]


@dataclass(frozen=True)
class DfActRecord:
    Tick: int
    Name: str
    Payload: object | None = None


@dataclass(frozen=True)
class DfRunResult:
    Status: RunStatus
    Tick: int
    Acts: tuple[DfActRecord, ...]
    Decisions: tuple["DfDecisionRecord", ...]
    StepCount: int
    FailureReason: object | None = None


@dataclass
class _RunAccumulator:
    Acts: list[DfActRecord] = field(default_factory=list)
    Decisions: list["DfDecisionRecord"] = field(default_factory=list)
    StepCount: int = 0


@dataclass(frozen=True)
class DfDecisionRecord:
    Tick: int
    Label: str
    Target: str
    Score: float


@dataclass
class _CommitmentState:
    Label: str
    Target: str
    Age: int


@dataclass
class DfRegistry:
    """Small explicit lookup surface for Push targets."""

    Nodes: dict[str, DfNodeFactory] = field(default_factory=dict)

    def Resolve(self, target: str) -> DfNodeFactory:
        if target not in self.Nodes:
            raise KeyError(f"Unknown Push target: {target}")
        return self.Nodes[target]


def RunNode(
    nodeFactory: DfNodeFactory,
    ctx: DfCtx | None = None,
    registry: DfRegistry | Mapping[str, DfNodeFactory] | None = None,
) -> DfRunResult:
    runCtx = ctx if ctx is not None else DfCtx()
    accumulator = _RunAccumulator()
    stack: list[DfNode] = [nodeFactory(runCtx)]
    commitmentByFrame: dict[int, _CommitmentState] = {}
    normalizedRegistry = _NormalizeRegistry(registry)

    while stack:
        node = stack[-1]
        try:
            op = next(node)
        except StopIteration:
            stack.pop()
            continue
        accumulator.StepCount += 1

        if isinstance(op, Act):
            accumulator.Acts.append(
                DfActRecord(
                    Tick=runCtx.Tick,
                    Name=op.Name,
                    Payload=op.Payload,
                )
            )
            continue

        if isinstance(op, Wait):
            _ApplyWait(runCtx, op)
            continue

        if isinstance(op, Push):
            pushFactory = normalizedRegistry.Resolve(op.Target)
            stack.append(pushFactory(runCtx))
            continue

        if isinstance(op, Decide):
            _ApplyDecide(
                ctx=runCtx,
                decideOp=op,
                normalizedRegistry=normalizedRegistry,
                stack=stack,
                commitmentByFrame=commitmentByFrame,
                accumulator=accumulator,
            )
            continue

        if isinstance(op, Pop):
            if len(stack) == 1:
                raise ValueError("Pop cannot be used at root")
            commitmentByFrame.pop(id(stack[-1]), None)
            stack.pop()
            continue

        if isinstance(op, Succeed):
            if len(stack) > 1:
                stack.pop()
                continue
            return DfRunResult(
                Status="Succeeded",
                Tick=runCtx.Tick,
                Acts=tuple(accumulator.Acts),
                Decisions=tuple(accumulator.Decisions),
                StepCount=accumulator.StepCount,
                FailureReason=None,
            )

        if isinstance(op, Fail):
            return DfRunResult(
                Status="Failed",
                Tick=runCtx.Tick,
                Acts=tuple(accumulator.Acts),
                Decisions=tuple(accumulator.Decisions),
                StepCount=accumulator.StepCount,
                FailureReason=op.Reason,
            )

        raise TypeError(f"Unsupported Dreadfang op for M1c runner: {type(op).__name__}")

    return DfRunResult(
        Status="Incomplete",
        Tick=runCtx.Tick,
        Acts=tuple(accumulator.Acts),
        Decisions=tuple(accumulator.Decisions),
        StepCount=accumulator.StepCount,
        FailureReason=None,
    )


def _ApplyWait(ctx: DfCtx, waitOp: Wait) -> None:
    if waitOp.Ticks < 0:
        raise ValueError("Wait ticks must be >= 0")

    ctx.Tick += waitOp.Ticks


def _ApplyDecide(
    ctx: DfCtx,
    decideOp: Decide,
    normalizedRegistry: DfRegistry,
    stack: list[DfNode],
    commitmentByFrame: dict[int, _CommitmentState],
    accumulator: _RunAccumulator,
) -> None:
    if len(decideOp.Options) == 0:
        raise ValueError("Decide requires at least one option")
    if decideOp.MinCommitTicks < 0:
        raise ValueError("Decide min_commit_ticks must be >= 0")
    if decideOp.Hysteresis < 0.0:
        raise ValueError("Decide hysteresis must be >= 0.0")

    frameId = id(stack[-1])
    scoredOptions = _ScoreOptions(decideOp.Options, ctx)
    rawBest = scoredOptions[0]
    committed = commitmentByFrame.get(frameId)

    chosen = rawBest
    if committed is not None:
        committedOption = _FindOption(scoredOptions, committed.Label, committed.Target)
        if committedOption is not None:
            if committed.Age < decideOp.MinCommitTicks:
                chosen = committedOption
            elif rawBest.Label != committed.Label or rawBest.Target != committed.Target:
                requiredScore = committedOption.Score + decideOp.Hysteresis
                if rawBest.Score < requiredScore:
                    chosen = committedOption

    if committed is not None and committed.Label == chosen.Label and committed.Target == chosen.Target:
        commitmentByFrame[frameId] = _CommitmentState(Label=chosen.Label, Target=chosen.Target, Age=committed.Age + 1)
    else:
        commitmentByFrame[frameId] = _CommitmentState(Label=chosen.Label, Target=chosen.Target, Age=0)

    accumulator.Decisions.append(
        DfDecisionRecord(
            Tick=ctx.Tick,
            Label=chosen.Label,
            Target=chosen.Target,
            Score=chosen.Score,
        )
    )

    pushFactory = normalizedRegistry.Resolve(chosen.Target)
    stack.append(pushFactory(ctx))


def _ScoreOptions(options: tuple[Option, ...], ctx: DfCtx) -> list[_ScoredOption]:
    scoredOptions = [
        _ScoredOption(Label=option.Label, Target=option.Target, Score=Clamp01(float(option.Score(ctx))))
        for option in options
    ]
    scoredOptions.sort(key=lambda candidate: candidate.Score, reverse=True)
    return scoredOptions


def _FindOption(
    options: list["_ScoredOption"],
    label: str,
    target: str,
) -> "_ScoredOption | None":
    for option in options:
        if option.Label == label and option.Target == target:
            return option
    return None


@dataclass(frozen=True)
class _ScoredOption:
    Label: str
    Target: str
    Score: float


def _NormalizeRegistry(
    registry: DfRegistry | Mapping[str, DfNodeFactory] | None,
) -> DfRegistry:
    if registry is None:
        return DfRegistry()

    if isinstance(registry, DfRegistry):
        return registry

    return DfRegistry(Nodes=dict(registry))

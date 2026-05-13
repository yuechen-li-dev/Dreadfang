from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Literal, Mapping

from dreadfang.core import (
    Act,
    Await,
    Clamp01,
    Decide,
    DfCondition,
    DfCtx,
    DfNode,
    Fail,
    Option,
    Pop,
    Push,
    StateAtLeast,
    StateAtMost,
    StateEquals,
    StateNotEquals,
    Succeed,
    Wait,
    WaitUntil,
)

RunStatus = Literal["Succeeded", "Failed", "Incomplete", "Waiting"]
DfNodeFactory = Callable[[DfCtx], DfNode]
DfActuatorFn = Callable[["DfActRecord", DfCtx], None]


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
    WaitingOn: str | None = None


@dataclass
class _RunAccumulator:
    Acts: list[DfActRecord] = field(default_factory=list)
    Decisions: list["DfDecisionRecord"] = field(default_factory=list)
    StepCount: int = 0


@dataclass(frozen=True)
class DfDecisionRecord:
    Tick: int
    Frame: str
    Label: str
    Target: str
    Score: float


@dataclass(frozen=True)
class DfFrameIdentity:
    Name: str
    Instance: int

    def ToKey(self) -> str:
        return f"{self.Name}#{self.Instance}"


@dataclass
class _FrameState:
    Identity: DfFrameIdentity
    Node: DfNode


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


@dataclass
class DfActuatorRegistry:
    """Small explicit lookup surface for Act handlers."""

    Handlers: dict[str, DfActuatorFn] = field(default_factory=dict)

    def Register(self, actName: str, handler: DfActuatorFn) -> None:
        self.Handlers[actName] = handler

    def Dispatch(self, act: DfActRecord, ctx: DfCtx) -> bool:
        handler = self.Handlers.get(act.Name)
        if handler is None:
            return False
        handler(act, ctx)
        return True


def RunNode(
    nodeFactory: DfNodeFactory,
    ctx: DfCtx | None = None,
    registry: DfRegistry | Mapping[str, DfNodeFactory] | None = None,
    actuators: DfActuatorRegistry | Mapping[str, DfActuatorFn] | None = None,
) -> DfRunResult:
    runCtx = ctx if ctx is not None else DfCtx()
    accumulator = _RunAccumulator()
    frameInstanceByName: dict[str, int] = {}
    rootIdentity = _NextFrameIdentity(nodeFactory.__name__, frameInstanceByName)
    stack: list[_FrameState] = [_FrameState(Identity=rootIdentity, Node=nodeFactory(runCtx))]
    commitmentByFrame: dict[DfFrameIdentity, _CommitmentState] = {}
    normalizedRegistry = _NormalizeRegistry(registry)
    normalizedActuators = _NormalizeActuatorRegistry(actuators)

    while stack:
        frame = stack[-1]
        node = frame.Node
        try:
            op = next(node)
        except StopIteration:
            stack.pop()
            continue
        accumulator.StepCount += 1

        if isinstance(op, Act):
            actRecord = DfActRecord(
                Tick=runCtx.Tick,
                Name=op.Name,
                Payload=op.Payload,
            )
            accumulator.Acts.append(actRecord)
            normalizedActuators.Dispatch(actRecord, runCtx)
            continue

        if isinstance(op, Wait):
            _ApplyWait(runCtx, op)
            continue

        if isinstance(op, Await):
            waited = _ApplyAwait(runCtx, op)
            if not waited:
                return DfRunResult(
                    Status="Waiting",
                    Tick=runCtx.Tick,
                    Acts=tuple(accumulator.Acts),
                    Decisions=tuple(accumulator.Decisions),
                    StepCount=accumulator.StepCount,
                    FailureReason=None,
                    WaitingOn=op.Name,
                )
            continue

        if isinstance(op, WaitUntil):
            if not _EvaluateCondition(runCtx, op.Condition):
                return DfRunResult(
                    Status="Waiting",
                    Tick=runCtx.Tick,
                    Acts=tuple(accumulator.Acts),
                    Decisions=tuple(accumulator.Decisions),
                    StepCount=accumulator.StepCount,
                    FailureReason=None,
                    WaitingOn=_DescribeCondition(op.Condition),
                )
            continue

        if isinstance(op, Push):
            pushFactory = normalizedRegistry.Resolve(op.Target)
            pushIdentity = _NextFrameIdentity(op.Target, frameInstanceByName)
            stack.append(_FrameState(Identity=pushIdentity, Node=pushFactory(runCtx)))
            continue

        if isinstance(op, Decide):
            _ApplyDecide(
                ctx=runCtx,
                decideOp=op,
                normalizedRegistry=normalizedRegistry,
                stack=stack,
                commitmentByFrame=commitmentByFrame,
                accumulator=accumulator,
                frameInstanceByName=frameInstanceByName,
            )
            continue

        if isinstance(op, Pop):
            if len(stack) == 1:
                raise ValueError("Pop cannot be used at root")
            commitmentByFrame.pop(stack[-1].Identity, None)
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
                WaitingOn=None,
            )

        if isinstance(op, Fail):
            return DfRunResult(
                Status="Failed",
                Tick=runCtx.Tick,
                Acts=tuple(accumulator.Acts),
                Decisions=tuple(accumulator.Decisions),
                StepCount=accumulator.StepCount,
                FailureReason=op.Reason,
                WaitingOn=None,
            )

        raise TypeError(f"Unsupported Dreadfang op for M1c runner: {type(op).__name__}")

    return DfRunResult(
        Status="Incomplete",
        Tick=runCtx.Tick,
        Acts=tuple(accumulator.Acts),
        Decisions=tuple(accumulator.Decisions),
        StepCount=accumulator.StepCount,
        FailureReason=None,
        WaitingOn=None,
    )


def _ApplyWait(ctx: DfCtx, waitOp: Wait) -> None:
    if waitOp.Ticks < 0:
        raise ValueError("Wait ticks must be >= 0")

    ctx.Tick += waitOp.Ticks


def _ApplyAwait(ctx: DfCtx, awaitOp: Await) -> bool:
    for index, message in enumerate(ctx.Mailbox):
        if message.Name != awaitOp.Name:
            continue
        ctx.LastMessage = message
        del ctx.Mailbox[index]
        return True
    return False


def _EvaluateCondition(ctx: DfCtx, condition: DfCondition) -> bool:
    if isinstance(condition, StateEquals):
        value = ctx.State.Get(condition.Key)
        return value == condition.Value
    if isinstance(condition, StateNotEquals):
        value = ctx.State.Get(condition.Key)
        return value != condition.Value
    if isinstance(condition, StateAtLeast):
        value = ctx.State.Get(condition.Key)
        return isinstance(value, (int, float)) and value >= condition.Value
    if isinstance(condition, StateAtMost):
        value = ctx.State.Get(condition.Key)
        return isinstance(value, (int, float)) and value <= condition.Value
    raise TypeError(f"Unsupported Dreadfang condition for runtime: {type(condition).__name__}")


def _DescribeCondition(condition: DfCondition) -> str:
    if isinstance(condition, StateEquals):
        return f"{condition.Key.Name} == {condition.Value!r}"
    if isinstance(condition, StateNotEquals):
        return f"{condition.Key.Name} != {condition.Value!r}"
    if isinstance(condition, StateAtLeast):
        return f"{condition.Key.Name} >= {condition.Value!r}"
    if isinstance(condition, StateAtMost):
        return f"{condition.Key.Name} <= {condition.Value!r}"
    return type(condition).__name__


def _ApplyDecide(
    ctx: DfCtx,
    decideOp: Decide,
    normalizedRegistry: DfRegistry,
    stack: list[_FrameState],
    commitmentByFrame: dict[DfFrameIdentity, _CommitmentState],
    accumulator: _RunAccumulator,
    frameInstanceByName: dict[str, int],
) -> None:
    if len(decideOp.Options) == 0:
        raise ValueError("Decide requires at least one option")
    if decideOp.MinCommitTicks < 0:
        raise ValueError("Decide min_commit_ticks must be >= 0")
    if decideOp.Hysteresis < 0.0:
        raise ValueError("Decide hysteresis must be >= 0.0")

    frameId = stack[-1].Identity
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
            Frame=frameId.ToKey(),
            Label=chosen.Label,
            Target=chosen.Target,
            Score=chosen.Score,
        )
    )

    pushFactory = normalizedRegistry.Resolve(chosen.Target)
    pushIdentity = _NextFrameIdentity(chosen.Target, frameInstanceByName)
    stack.append(_FrameState(Identity=pushIdentity, Node=pushFactory(ctx)))


def _NextFrameIdentity(name: str, frameInstanceByName: dict[str, int]) -> DfFrameIdentity:
    currentCount = frameInstanceByName.get(name, 0)
    frameInstanceByName[name] = currentCount + 1
    return DfFrameIdentity(Name=name, Instance=currentCount)


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


def _NormalizeActuatorRegistry(
    actuators: DfActuatorRegistry | Mapping[str, DfActuatorFn] | None,
) -> DfActuatorRegistry:
    if actuators is None:
        return DfActuatorRegistry()

    if isinstance(actuators, DfActuatorRegistry):
        return actuators

    return DfActuatorRegistry(Handlers=dict(actuators))

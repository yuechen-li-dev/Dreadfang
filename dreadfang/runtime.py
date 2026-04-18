from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Literal, Mapping

from dreadfang.core import Act, DfCtx, DfNode, DfOp, Fail, Pop, Push, Succeed, Wait

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
    StepCount: int
    FailureReason: object | None = None


@dataclass
class _RunAccumulator:
    Acts: list[DfActRecord] = field(default_factory=list)
    StepCount: int = 0


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

        if isinstance(op, Pop):
            if len(stack) == 1:
                raise ValueError("Pop cannot be used at root")
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
                StepCount=accumulator.StepCount,
                FailureReason=None,
            )

        if isinstance(op, Fail):
            return DfRunResult(
                Status="Failed",
                Tick=runCtx.Tick,
                Acts=tuple(accumulator.Acts),
                StepCount=accumulator.StepCount,
                FailureReason=op.Reason,
            )

        raise TypeError(f"Unsupported Dreadfang op for M1c runner: {type(op).__name__}")

    return DfRunResult(
        Status="Incomplete",
        Tick=runCtx.Tick,
        Acts=tuple(accumulator.Acts),
        StepCount=accumulator.StepCount,
        FailureReason=None,
    )


def _ApplyWait(ctx: DfCtx, waitOp: Wait) -> None:
    if waitOp.Ticks < 0:
        raise ValueError("Wait ticks must be >= 0")

    ctx.Tick += waitOp.Ticks


def _NormalizeRegistry(
    registry: DfRegistry | Mapping[str, DfNodeFactory] | None,
) -> DfRegistry:
    if registry is None:
        return DfRegistry()

    if isinstance(registry, DfRegistry):
        return registry

    return DfRegistry(Nodes=dict(registry))

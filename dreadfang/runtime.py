from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Literal

from dreadfang.core import Act, DfCtx, DfNode, DfOp, Fail, Succeed, Wait

RunStatus = Literal["Succeeded", "Failed", "Incomplete"]


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


def RunNode(
    nodeFactory: Callable[[DfCtx], DfNode],
    ctx: DfCtx | None = None,
) -> DfRunResult:
    runCtx = ctx if ctx is not None else DfCtx()
    node = nodeFactory(runCtx)
    accumulator = _RunAccumulator()

    for op in node:
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

        if isinstance(op, Succeed):
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

        raise TypeError(f"Unsupported Dreadfang op for M1b runner: {type(op).__name__}")

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

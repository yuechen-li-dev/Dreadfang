from __future__ import annotations

from dreadfang.core import Df, DfCtx, DfNode
from dreadfang.runtime import DfNodeFactory, DfRegistry


def Root(ctx: DfCtx) -> DfNode:
    if ctx.State.Get("mode") is None:
        ctx.State.Set("mode", "patrol")

    if ctx.State.Get("recoverAttempts") is None:
        ctx.State.Set("recoverAttempts", 0)

    yield Df.Act("RootStart", {"mode": ctx.State.Get("mode")})
    yield from PatrolBeat(ctx)

    if bool(ctx.State.Get("targetLost", False)):
        yield Df.Push("RecoverBeat")

    yield Df.Act("RootDone", {"mode": ctx.State.Get("mode")})
    yield Df.Succeed()


def PatrolBeat(ctx: DfCtx) -> DfNode:
    yield Df.Act("PatrolLook")
    yield Df.Wait(1)
    yield Df.Act("PatrolStep", {"lane": ctx.State.Get("lane", "north")})

    if bool(ctx.State.Get("forceRecover", False)):
        ctx.State.Set("targetLost", True)
        yield Df.Act("TargetLost")
    else:
        ctx.State.Set("targetLost", False)
        yield Df.Act("TargetVisible")


def RecoverBeat(ctx: DfCtx) -> DfNode:
    recoverAttempts = int(ctx.State.Get("recoverAttempts", 0)) + 1
    ctx.State.Set("recoverAttempts", recoverAttempts)

    yield Df.Act("RecoverSweep", {"attempt": recoverAttempts})
    yield Df.Wait(2)

    if recoverAttempts >= 2:
        ctx.State.Set("mode", "fallback")
        yield Df.Act("RecoverFallback")
    else:
        ctx.State.Set("mode", "patrol")
        yield Df.Act("RecoverLock")

    yield Df.Pop({"recoverAttempts": recoverAttempts})


def BuildRegistry() -> DfRegistry:
    nodes: dict[str, DfNodeFactory] = {
        "RecoverBeat": RecoverBeat,
    }
    return DfRegistry(Nodes=nodes)

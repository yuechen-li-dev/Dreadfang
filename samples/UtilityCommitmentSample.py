from __future__ import annotations

from dataclasses import dataclass

from dreadfang.core import Df, DfCtx, DfNode
from dreadfang.runtime import DfNodeFactory, DfRegistry, DfRunResult, RunNode


@dataclass(frozen=True)
class UtilitySampleConfig:
    Hysteresis: float
    MinCommitTicks: int


@dataclass(frozen=True)
class UtilitySampleOutcome:
    Result: DfRunResult
    SelectedLabels: tuple[str, ...]
    SwitchCount: int


def TrackScore(ctx: DfCtx) -> float:
    signal = float(ctx.State.Get("signal", 0.0))
    return signal


def RecoverScore(ctx: DfCtx) -> float:
    signal = float(ctx.State.Get("signal", 0.0))
    return 1.0 - signal


def Root(ctx: DfCtx) -> DfNode:
    signalSeriesRaw = ctx.State.Get("signalSeries", ())
    signalSeries = tuple(float(value) for value in signalSeriesRaw) if isinstance(signalSeriesRaw, tuple) else ()
    configRaw = ctx.State.Get("utilityConfig")
    if not isinstance(configRaw, UtilitySampleConfig):
        raise TypeError("utilityConfig must be UtilitySampleConfig")

    for signal in signalSeries:
        ctx.State.Set("signal", signal)
        yield Df.Act("SignalObserved", {"signal": signal})
        yield Df.Decide(
            [
                Df.Option("Track", TrackScore, "TrackBeat"),
                Df.Option("Recover", RecoverScore, "RecoverBeat"),
            ],
            hysteresis=configRaw.Hysteresis,
            min_commit_ticks=configRaw.MinCommitTicks,
        )
        yield Df.Wait(1)

    yield Df.Succeed()


def TrackBeat(_ctx: DfCtx) -> DfNode:
    yield Df.Act("TrackBeat")
    yield Df.Pop()


def RecoverBeat(_ctx: DfCtx) -> DfNode:
    yield Df.Act("RecoverBeat")
    yield Df.Pop()


def BuildRegistry() -> DfRegistry:
    nodes: dict[str, DfNodeFactory] = {
        "TrackBeat": TrackBeat,
        "RecoverBeat": RecoverBeat,
    }
    return DfRegistry(Nodes=nodes)


def RunUtilitySample(config: UtilitySampleConfig, signalSeries: tuple[float, ...]) -> UtilitySampleOutcome:
    ctx = DfCtx()
    ctx.State.Set("utilityConfig", config)
    ctx.State.Set("signalSeries", signalSeries)

    result = RunNode(Root, ctx=ctx, registry=BuildRegistry())
    selectedLabels = tuple(record.Label for record in result.Decisions)
    switchCount = _CountLabelSwitches(selectedLabels)

    return UtilitySampleOutcome(
        Result=result,
        SelectedLabels=selectedLabels,
        SwitchCount=switchCount,
    )


def _CountLabelSwitches(labels: tuple[str, ...]) -> int:
    if len(labels) < 2:
        return 0

    switches = 0
    previous = labels[0]
    for current in labels[1:]:
        if current != previous:
            switches += 1
        previous = current
    return switches

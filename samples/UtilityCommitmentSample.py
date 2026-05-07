from __future__ import annotations

from dataclasses import dataclass

from dreadfang.core import Df, DfCtx
from dreadfang.runtime import DfNodeFactory, DfRegistry, DfRunResult, RunNode
import samples.UtilityCommitmentNodes as UtilityCommitmentNodes

UtilityCommitmentNodes.Df = Df
Root = UtilityCommitmentNodes.Root
TrackBeat = UtilityCommitmentNodes.TrackBeat
RecoverBeat = UtilityCommitmentNodes.RecoverBeat


@dataclass(frozen=True)
class UtilitySampleConfig:
    Hysteresis: float
    MinCommitTicks: int


@dataclass(frozen=True)
class UtilitySampleOutcome:
    Result: DfRunResult
    SelectedLabels: tuple[str, ...]
    SwitchCount: int


def BuildRegistry() -> DfRegistry:
    nodes: dict[str, DfNodeFactory] = {
        "TrackBeat": TrackBeat,
        "RecoverBeat": RecoverBeat,
    }
    return DfRegistry(Nodes=nodes)


def RunUtilitySample(config: UtilitySampleConfig, signalSeries: tuple[float, ...]) -> UtilitySampleOutcome:
    ctx = DfCtx()
    ctx.State.Set("hysteresis", config.Hysteresis)
    ctx.State.Set("minCommitTicks", config.MinCommitTicks)
    ctx.State.Set("signalSeries", signalSeries)

    result = RunNode(Root, ctx=ctx, registry=BuildRegistry())
    selectedLabels = tuple(record.Label for record in result.Decisions)
    switchCount = CountLabelSwitches(selectedLabels)

    return UtilitySampleOutcome(
        Result=result,
        SelectedLabels=selectedLabels,
        SwitchCount=switchCount,
    )


def CountLabelSwitches(labels: tuple[str, ...]) -> int:
    if len(labels) < 2:
        return 0

    switches = 0
    previous = labels[0]
    for current in labels[1:]:
        if current != previous:
            switches += 1
        previous = current
    return switches

from __future__ import annotations

import pytest

from dreadfang.core import Df, DfCtx, DfNode, Event
from dreadfang.runtime import DfActRecord, RunNode


def test_RunNodeActWaitSucceedDeterministic() -> None:
    def PatrolNode(_ctx: DfCtx) -> DfNode:
        yield Df.Act("Look")
        yield Df.Wait(2)
        yield Df.Act("Move", {"to": "east"})
        yield Df.Succeed("done")

    result = RunNode(PatrolNode)

    assert result.Status == "Succeeded"
    assert result.Tick == 2
    assert result.StepCount == 4
    assert result.FailureReason is None
    assert result.Acts == (
        DfActRecord(Tick=0, Name="Look", Payload=None),
        DfActRecord(Tick=2, Name="Move", Payload={"to": "east"}),
    )


def test_RunNodeFailStopsAndPreservesReason() -> None:
    def FailingNode(_ctx: DfCtx) -> DfNode:
        yield Df.Act("Start")
        yield Df.Fail("boom")
        yield Df.Act("Never")

    result = RunNode(FailingNode)

    assert result.Status == "Failed"
    assert result.Tick == 0
    assert result.StepCount == 2
    assert result.FailureReason == "boom"
    assert result.Acts == (DfActRecord(Tick=0, Name="Start", Payload=None),)


def test_RunNodeSucceedStopsWithoutExtraSteps() -> None:
    def SuccessNode(_ctx: DfCtx) -> DfNode:
        yield Df.Wait(1)
        yield Df.Succeed()
        yield Df.Wait(3)

    result = RunNode(SuccessNode)

    assert result.Status == "Succeeded"
    assert result.Tick == 1
    assert result.StepCount == 2
    assert result.Acts == ()


def test_RunNodeUsesProvidedCtxAndMutatesTick() -> None:
    ctx = DfCtx()

    def WaitNode(nodeCtx: DfCtx) -> DfNode:
        assert nodeCtx is ctx
        yield Df.Wait(1)
        yield Df.Wait(3)
        yield Df.Succeed()

    result = RunNode(WaitNode, ctx)

    assert result.Status == "Succeeded"
    assert result.Tick == 4
    assert ctx.Tick == 4


def test_RunNodeIncompleteWhenNodeExhaustsWithoutTerminalOp() -> None:
    def IncompleteNode(_ctx: DfCtx) -> DfNode:
        yield Df.Act("Only")

    result = RunNode(IncompleteNode)

    assert result.Status == "Incomplete"
    assert result.StepCount == 1
    assert result.Acts == (DfActRecord(Tick=0, Name="Only", Payload=None),)


def test_RunNodeRejectsUnsupportedOpsInM1b() -> None:
    def UnsupportedNode(_ctx: DfCtx) -> DfNode:
        yield Event(Name="Noise")

    with pytest.raises(TypeError):
        _ = RunNode(UnsupportedNode)


def test_RunNodeRejectsNegativeWaitTicks() -> None:
    def BadWaitNode(_ctx: DfCtx) -> DfNode:
        yield Df.Wait(-1)

    with pytest.raises(ValueError):
        _ = RunNode(BadWaitNode)

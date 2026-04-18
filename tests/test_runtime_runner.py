from __future__ import annotations

import pytest

from dreadfang.core import Df, DfCtx, DfNode, Event
from dreadfang.runtime import DfActRecord, DfRegistry, RunNode


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


def test_RunNodeSupportsYieldFromLinearComposition() -> None:
    def ChildNode(_ctx: DfCtx) -> DfNode:
        yield Df.Act("ChildStart")
        yield Df.Wait(2)
        yield Df.Act("ChildEnd")

    def ParentNode(ctx: DfCtx) -> DfNode:
        yield Df.Act("ParentStart")
        yield from ChildNode(ctx)
        yield Df.Act("ParentEnd")
        yield Df.Succeed()

    result = RunNode(ParentNode)

    assert result.Status == "Succeeded"
    assert result.Tick == 2
    assert result.StepCount == 6
    assert result.Acts == (
        DfActRecord(Tick=0, Name="ParentStart", Payload=None),
        DfActRecord(Tick=0, Name="ChildStart", Payload=None),
        DfActRecord(Tick=2, Name="ChildEnd", Payload=None),
        DfActRecord(Tick=2, Name="ParentEnd", Payload=None),
    )


def test_RunNodePushPopSuspendsAndResumesParent() -> None:
    def ParentNode(_ctx: DfCtx) -> DfNode:
        yield Df.Act("ParentStart")
        yield Df.Push("Child")
        yield Df.Act("ParentResume")
        yield Df.Succeed()

    def ChildNode(_ctx: DfCtx) -> DfNode:
        yield Df.Act("ChildAct")
        yield Df.Pop()

    result = RunNode(ParentNode, registry={"Child": ChildNode})

    assert result.Status == "Succeeded"
    assert result.StepCount == 6
    assert result.Acts == (
        DfActRecord(Tick=0, Name="ParentStart", Payload=None),
        DfActRecord(Tick=0, Name="ChildAct", Payload=None),
        DfActRecord(Tick=0, Name="ParentResume", Payload=None),
    )


def test_RunNodePushPopNestedSubroutinesAreOrdered() -> None:
    def ParentNode(_ctx: DfCtx) -> DfNode:
        yield Df.Act("P1")
        yield Df.Push("Child")
        yield Df.Act("P2")
        yield Df.Succeed()

    def ChildNode(_ctx: DfCtx) -> DfNode:
        yield Df.Act("C1")
        yield Df.Push("Grandchild")
        yield Df.Act("C2")
        yield Df.Pop()

    def GrandchildNode(_ctx: DfCtx) -> DfNode:
        yield Df.Act("G1")
        yield Df.Pop()

    registry = DfRegistry(
        Nodes={
            "Child": ChildNode,
            "Grandchild": GrandchildNode,
        }
    )

    result = RunNode(ParentNode, registry=registry)

    assert result.Status == "Succeeded"
    assert tuple(record.Name for record in result.Acts) == ("P1", "C1", "G1", "C2", "P2")


def test_RunNodeChildFailFailsWholeRun() -> None:
    def ParentNode(_ctx: DfCtx) -> DfNode:
        yield Df.Act("ParentStart")
        yield Df.Push("Child")
        yield Df.Act("Never")
        yield Df.Succeed()

    def ChildNode(_ctx: DfCtx) -> DfNode:
        yield Df.Fail("child failed")

    result = RunNode(ParentNode, registry={"Child": ChildNode})

    assert result.Status == "Failed"
    assert result.FailureReason == "child failed"
    assert result.Acts == (DfActRecord(Tick=0, Name="ParentStart", Payload=None),)


def test_RunNodePopAtRootRaisesExplicitError() -> None:
    def BadNode(_ctx: DfCtx) -> DfNode:
        yield Df.Pop()

    with pytest.raises(ValueError, match="Pop cannot be used at root"):
        _ = RunNode(BadNode)


def test_RunNodePushRequiresKnownTarget() -> None:
    def ParentNode(_ctx: DfCtx) -> DfNode:
        yield Df.Push("Missing")

    with pytest.raises(KeyError, match="Unknown Push target"):
        _ = RunNode(ParentNode)

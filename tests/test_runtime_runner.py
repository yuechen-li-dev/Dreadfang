from __future__ import annotations

import pytest

from dreadfang.core import Df, DfCtx, DfNode, Event, When
from dreadfang.runtime import DfActRecord, DfActuatorRegistry, DfDecisionRecord, DfRegistry, RunNode


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
    assert result.Decisions == ()


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
    assert result.Decisions == ()


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
    assert result.Decisions == ()


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
    assert result.Decisions == ()


def test_RunNodeRejectsUnsupportedOpsInM1b() -> None:
    def UnsupportedNode(_ctx: DfCtx) -> DfNode:
        yield Event(Name="Noise")

    with pytest.raises(TypeError):
        _ = RunNode(UnsupportedNode)


def test_RunNodeAwaitConsumesMessageAndSetsLastMessage() -> None:
    def Root(ctx: DfCtx) -> DfNode:
        yield Df.Await("Choice")
        yield Df.Act("SawChoice", ctx.LastMessage.Payload)
        yield Df.Succeed()

    ctx = DfCtx(
        Mailbox=[
            Df.Message("Noise", 1),
            Df.Message("Choice", "proud"),
            Df.Message("Noise", 2),
            Df.Message("Choice", "late"),
        ]
    )
    result = RunNode(Root, ctx=ctx)

    assert result.Status == "Succeeded"
    assert result.Acts == (DfActRecord(Tick=0, Name="SawChoice", Payload="proud"),)
    assert ctx.LastMessage == Df.Message("Choice", "proud")
    assert ctx.Mailbox == [Df.Message("Noise", 1), Df.Message("Noise", 2), Df.Message("Choice", "late")]


def test_RunNodeAwaitMissingMessageReturnsWaitingAndPreservesActs() -> None:
    def Root(_ctx: DfCtx) -> DfNode:
        yield Df.Act("BeforeWait")
        yield Df.Await("Choice")
        yield Df.Act("AfterWait")
        yield Df.Succeed()

    ctx = DfCtx(Mailbox=[Df.Message("Noise", 7)])
    result = RunNode(Root, ctx=ctx)

    assert result.Status == "Waiting"
    assert result.WaitingOn == "Choice"
    assert result.StepCount == 2
    assert result.FailureReason is None
    assert result.Acts == (DfActRecord(Tick=0, Name="BeforeWait", Payload=None),)
    assert ctx.LastMessage is None
    assert ctx.Mailbox == [Df.Message("Noise", 7)]


def test_RunNodeWaitUntilTrueContinuesInSameInvocation() -> None:
    ready = Df.Key("Ready", bool)

    def Root(ctx: DfCtx) -> DfNode:
        ctx.State.Set(ready, True)
        yield Df.WaitUntil(Df.StateEquals(ready, True))
        yield Df.Act("AfterCondition")
        yield Df.Succeed()

    result = RunNode(Root)
    assert result.Status == "Succeeded"
    assert result.Tick == 0
    assert result.Acts == (DfActRecord(Tick=0, Name="AfterCondition", Payload=None),)


def test_RunNodeWaitUntilFalseReturnsWaitingAndPreservesPriorActs() -> None:
    ready = Df.Key("Ready", bool)

    def Root(_ctx: DfCtx) -> DfNode:
        yield Df.Act("BeforeCondition")
        yield Df.WaitUntil(Df.StateEquals(ready, True))
        yield Df.Act("AfterCondition")
        yield Df.Succeed()

    result = RunNode(Root)
    assert result.Status == "Waiting"
    assert result.WaitingOn == "Ready == True"
    assert result.Acts == (DfActRecord(Tick=0, Name="BeforeCondition", Payload=None),)


def test_RunNodeWaitUntilMissingKeyBehaviorIsDeterministic() -> None:
    signal = Df.Key("Signal", float)

    def Root(_ctx: DfCtx) -> DfNode:
        yield Df.WaitUntil(Df.StateAtLeast(signal, 0.75))
        yield Df.Succeed()

    result = RunNode(Root)
    assert result.Status == "Waiting"
    assert result.WaitingOn == "Signal >= 0.75"


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


def test_RunNodeDecideChoosesHighestClampedScore() -> None:
    def HighSignal(ctx: DfCtx) -> float:
        return float(ctx.State.Get("signal", 0.0))

    def Root(_ctx: DfCtx) -> DfNode:
        yield Df.Decide(
            [
                Df.Option("Primary", HighSignal, "PrimaryBeat"),
                Df.Option("Fallback", When.Always, "FallbackBeat"),
            ]
        )
        yield Df.Succeed()

    def PrimaryBeat(_ctx: DfCtx) -> DfNode:
        yield Df.Act("Primary")
        yield Df.Pop()

    def FallbackBeat(_ctx: DfCtx) -> DfNode:
        yield Df.Act("Fallback")
        yield Df.Pop()

    ctx = DfCtx()
    ctx.State.Set("signal", 2.5)

    result = RunNode(Root, ctx=ctx, registry={"PrimaryBeat": PrimaryBeat, "FallbackBeat": FallbackBeat})

    assert result.Status == "Succeeded"
    assert result.Decisions == (
        DfDecisionRecord(Tick=0, Frame="Root#0", Label="Primary", Target="PrimaryBeat", Score=1.0),
    )
    assert result.Acts == (DfActRecord(Tick=0, Name="Primary", Payload=None),)


def test_RunNodeDecideHysteresisRetainsCommitUntilMarginIsBeaten() -> None:
    def PrimaryScore(ctx: DfCtx) -> float:
        return float(ctx.State.Get("primary", 0.0))

    def FallbackScore(ctx: DfCtx) -> float:
        return float(ctx.State.Get("fallback", 0.0))

    def Root(ctx: DfCtx) -> DfNode:
        yield Df.Decide(
            [
                Df.Option("Primary", PrimaryScore, "PrimaryBeat"),
                Df.Option("Fallback", FallbackScore, "FallbackBeat"),
            ],
            hysteresis=0.1,
        )
        ctx.State.Set("primary", 0.60)
        ctx.State.Set("fallback", 0.65)
        yield Df.Decide(
            [
                Df.Option("Primary", PrimaryScore, "PrimaryBeat"),
                Df.Option("Fallback", FallbackScore, "FallbackBeat"),
            ],
            hysteresis=0.1,
        )
        ctx.State.Set("fallback", 0.72)
        yield Df.Decide(
            [
                Df.Option("Primary", PrimaryScore, "PrimaryBeat"),
                Df.Option("Fallback", FallbackScore, "FallbackBeat"),
            ],
            hysteresis=0.1,
        )
        yield Df.Succeed()

    def PrimaryBeat(_ctx: DfCtx) -> DfNode:
        yield Df.Act("Primary")
        yield Df.Pop()

    def FallbackBeat(_ctx: DfCtx) -> DfNode:
        yield Df.Act("Fallback")
        yield Df.Pop()

    ctx = DfCtx()
    ctx.State.Set("primary", 0.60)
    ctx.State.Set("fallback", 0.58)

    result = RunNode(Root, ctx=ctx, registry={"PrimaryBeat": PrimaryBeat, "FallbackBeat": FallbackBeat})

    assert tuple(record.Name for record in result.Acts) == ("Primary", "Primary", "Fallback")
    assert result.Decisions == (
        DfDecisionRecord(Tick=0, Frame="Root#0", Label="Primary", Target="PrimaryBeat", Score=0.6),
        DfDecisionRecord(Tick=0, Frame="Root#0", Label="Primary", Target="PrimaryBeat", Score=0.6),
        DfDecisionRecord(Tick=0, Frame="Root#0", Label="Fallback", Target="FallbackBeat", Score=0.72),
    )


def test_RunNodeDecideMinCommitBlocksSwitchUntilWindowElapses() -> None:
    def PrimaryScore(ctx: DfCtx) -> float:
        return float(ctx.State.Get("primary", 0.0))

    def FallbackScore(ctx: DfCtx) -> float:
        return float(ctx.State.Get("fallback", 0.0))

    def Root(ctx: DfCtx) -> DfNode:
        yield Df.Decide(
            [
                Df.Option("Primary", PrimaryScore, "PrimaryBeat"),
                Df.Option("Fallback", FallbackScore, "FallbackBeat"),
            ],
            min_commit_ticks=2,
        )
        ctx.State.Set("fallback", 1.0)
        yield Df.Decide(
            [
                Df.Option("Primary", PrimaryScore, "PrimaryBeat"),
                Df.Option("Fallback", FallbackScore, "FallbackBeat"),
            ],
            min_commit_ticks=2,
        )
        yield Df.Decide(
            [
                Df.Option("Primary", PrimaryScore, "PrimaryBeat"),
                Df.Option("Fallback", FallbackScore, "FallbackBeat"),
            ],
            min_commit_ticks=2,
        )
        yield Df.Decide(
            [
                Df.Option("Primary", PrimaryScore, "PrimaryBeat"),
                Df.Option("Fallback", FallbackScore, "FallbackBeat"),
            ],
            min_commit_ticks=2,
        )
        yield Df.Succeed()

    def PrimaryBeat(_ctx: DfCtx) -> DfNode:
        yield Df.Act("Primary")
        yield Df.Pop()

    def FallbackBeat(_ctx: DfCtx) -> DfNode:
        yield Df.Act("Fallback")
        yield Df.Pop()

    ctx = DfCtx()
    ctx.State.Set("primary", 0.7)
    ctx.State.Set("fallback", 0.0)

    result = RunNode(Root, ctx=ctx, registry={"PrimaryBeat": PrimaryBeat, "FallbackBeat": FallbackBeat})

    assert tuple(record.Name for record in result.Acts) == ("Primary", "Primary", "Primary", "Fallback")
    assert tuple(record.Label for record in result.Decisions) == ("Primary", "Primary", "Primary", "Fallback")


def test_RunNodeDecideFrameIdentityStableAcrossEquivalentRuns() -> None:
    def Root(_ctx: DfCtx) -> DfNode:
        yield Df.Decide([Df.Option("Primary", When.Always, "PrimaryBeat")])
        yield Df.Succeed()

    def PrimaryBeat(_ctx: DfCtx) -> DfNode:
        yield Df.Pop()

    first = RunNode(Root, registry={"PrimaryBeat": PrimaryBeat})
    second = RunNode(Root, registry={"PrimaryBeat": PrimaryBeat})

    assert tuple(record.Frame for record in first.Decisions) == ("Root#0",)
    assert tuple(record.Frame for record in second.Decisions) == ("Root#0",)
    assert first.Decisions == second.Decisions


def test_RunNodeDecideSeparateFramesDoNotShareCommitment() -> None:
    def Child(_ctx: DfCtx) -> DfNode:
        yield Df.Decide([Df.Option("Fallback", When.Always, "FallbackBeat")], min_commit_ticks=2)
        yield Df.Pop()

    def Root(_ctx: DfCtx) -> DfNode:
        yield Df.Decide([Df.Option("Primary", When.Always, "PrimaryBeat")], min_commit_ticks=2)
        yield Df.Push("Child")
        yield Df.Succeed()

    def PrimaryBeat(_ctx: DfCtx) -> DfNode:
        yield Df.Pop()

    def FallbackBeat(_ctx: DfCtx) -> DfNode:
        yield Df.Pop()

    result = RunNode(Root, registry={"PrimaryBeat": PrimaryBeat, "FallbackBeat": FallbackBeat, "Child": Child})

    assert tuple(record.Frame for record in result.Decisions) == ("Root#0", "Child#0")


def test_RunNodeActuatorDispatchIsOptionalAndRecordFirst() -> None:
    dispatchNames: list[str] = []

    def Root(_ctx: DfCtx) -> DfNode:
        yield Df.Act("Line", "A")
        yield Df.Act("Line", "B")
        yield Df.Succeed()

    noActuators = RunNode(Root)

    assert noActuators.Acts == (
        DfActRecord(Tick=0, Name="Line", Payload="A"),
        DfActRecord(Tick=0, Name="Line", Payload="B"),
    )

    def EmitLine(record: DfActRecord, _ctx: DfCtx) -> None:
        dispatchNames.append(record.Payload if isinstance(record.Payload, str) else "")

    actuators = DfActuatorRegistry()
    actuators.Register("Line", EmitLine)

    withActuators = RunNode(Root, actuators=actuators)

    assert withActuators.Acts == noActuators.Acts
    assert dispatchNames == ["A", "B"]


def test_RunNodeActuatorHandlerReceivesCtxAndOrderedActs() -> None:
    seen: list[tuple[int, str, int]] = []
    ctx = DfCtx()

    def Root(_ctx: DfCtx) -> DfNode:
        yield Df.Act("Line", "first")
        yield Df.Wait(2)
        yield Df.Act("Line", "second")
        yield Df.Succeed()

    def Capture(record: DfActRecord, captureCtx: DfCtx) -> None:
        seen.append((record.Tick, str(record.Payload), captureCtx.Tick))

    result = RunNode(Root, ctx=ctx, actuators={"Line": Capture})

    assert result.Status == "Succeeded"
    assert seen == [(0, "first", 0), (2, "second", 2)]


def test_RunNodeUnknownActuatorIsExplicitNoOp() -> None:
    called: list[str] = []

    def Root(_ctx: DfCtx) -> DfNode:
        yield Df.Act("Known", "K")
        yield Df.Act("Unknown", "U")
        yield Df.Succeed()

    def HandleKnown(record: DfActRecord, _ctx: DfCtx) -> None:
        called.append(str(record.Payload))

    result = RunNode(Root, actuators={"Known": HandleKnown})

    assert result.Acts == (
        DfActRecord(Tick=0, Name="Known", Payload="K"),
        DfActRecord(Tick=0, Name="Unknown", Payload="U"),
    )
    assert called == ["K"]


def test_RunNodeActuatorFailurePropagates() -> None:
    def Root(_ctx: DfCtx) -> DfNode:
        yield Df.Act("Boom")
        yield Df.Succeed()

    def RaiseActuator(_record: DfActRecord, _ctx: DfCtx) -> None:
        raise RuntimeError("actuator failed")

    with pytest.raises(RuntimeError, match="actuator failed"):
        _ = RunNode(Root, actuators={"Boom": RaiseActuator})

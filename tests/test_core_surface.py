from __future__ import annotations

from dataclasses import is_dataclass
from typing import cast

from dreadfang.core import (
    Act,
    Await,
    Clamp01,
    Decide,
    Df,
    DfKey,
    DfMessage,
    DfCtx,
    DfNode,
    DfState,
    Event,
    Fail,
    Option,
    Pop,
    Push,
    Succeed,
    Until,
    Wait,
    When,
)


def test_DfStateGetSet() -> None:
    state = DfState()

    assert state.Get("missing") is None
    assert state.Get("missing", 42) == 42

    state.Set("hp", 10)
    assert state.Get("hp") == 10


def test_DfKeyAndTypedDfStateAccess() -> None:
    state = DfState()
    mode = Df.Key("Mode", str)
    recoverAttempts = Df.Key("RecoverAttempts", int)
    signal = Df.Key("Signal", float)
    forceRecover = Df.Key("ForceRecover", bool)

    assert isinstance(mode, DfKey)
    assert mode.Name == "Mode"
    assert mode.ValueType is str

    state.Set(mode, "patrol")
    state.Set(recoverAttempts, 1)
    state.Set(signal, 0.5)
    state.Set(forceRecover, True)

    assert state.Get(mode, "idle") == "patrol"
    assert state.Get(recoverAttempts, 0) == 1
    assert state.Get(signal, 0.0) == 0.5
    assert state.Get(forceRecover, False) is True


def test_DfStateTypedDefaultAndTypeErrors() -> None:
    state = DfState()
    recoverAttempts = Df.Key("RecoverAttempts", int)

    assert state.Get(recoverAttempts, 0) == 0

    try:
        state.Set(recoverAttempts, "one")
        assert False, "expected TypeError"
    except TypeError as error:
        assert "expects int value" in str(error)

    try:
        state.Get(recoverAttempts, "zero")
        assert False, "expected TypeError"
    except TypeError as error:
        assert "expects int default" in str(error)


def test_DfStateTypedNameCollisionDetected() -> None:
    state = DfState()
    modeAsStr = Df.Key("Mode", str)
    modeAsStr2 = Df.Key("Mode", str)
    modeAsInt = Df.Key("Mode", int)

    state.Set(modeAsStr, "patrol")
    state.Set(modeAsStr2, "recover")

    try:
        state.Get(modeAsInt, 0)
        assert False, "expected TypeError"
    except TypeError as error:
        assert "already registered with type str" in str(error)


def test_DfCtxDefaults() -> None:
    ctx = DfCtx()

    assert isinstance(ctx.State, DfState)
    assert ctx.Mailbox == []
    assert ctx.LastMessage is None
    assert ctx.Tick == 0


def test_DfMessageHelperProducesMessageRecord() -> None:
    message = Df.Message("Choice", "proud")

    assert isinstance(message, DfMessage)
    assert message.Name == "Choice"
    assert message.Payload == "proud"


def test_OpDataclassShape() -> None:
    assert is_dataclass(Push)
    assert Push(Target="Combat").Target == "Combat"
    assert Pop(Payload={"ok": True}).Payload == {"ok": True}
    assert Succeed(Payload="done").Payload == "done"
    failure = Fail(Reason="because", Payload={"k": "v"})
    assert failure.Reason == "because"
    assert failure.Payload == {"k": "v"}
    assert Wait(Ticks=3).Ticks == 3

    until = Until(Predicate=lambda _ctx: True)
    assert until.Predicate(DfCtx()) is True

    assert Act(Name="Move", Payload={"to": "north"}).Name == "Move"
    assert Event(Name="SawTarget", Payload={"id": "w1"}).Payload == {"id": "w1"}
    assert Await(Name="SawTarget", TimeoutTicks=5).TimeoutTicks == 5


def test_DfHelpersProduceExpectedOps() -> None:
    assert Df.Wait(2) == Wait(Ticks=2)
    assert Df.Act("Move", {"to": "east"}) == Act(Name="Move", Payload={"to": "east"})
    assert Df.Succeed() == Succeed(Payload=None)
    assert Df.Fail("bad", {"code": 1}) == Fail(Reason="bad", Payload={"code": 1})


def test_DfDecideNormalizesOptions() -> None:
    optionA = Df.Option("Primary", When.Always, "PrimaryBeat")
    optionB = Df.Option("Fallback", When.Never, "FallbackBeat")

    decide = Df.Decide(optionA, [optionB], hysteresis=0.1, min_commit_ticks=2)

    assert isinstance(decide, Decide)
    assert decide.Options == (optionA, optionB)
    assert decide.Hysteresis == 0.1
    assert decide.MinCommitTicks == 2


def test_Clamp01AndWhenHelpers() -> None:
    assert Clamp01(-2.5) == 0.0
    assert Clamp01(0.4) == 0.4
    assert Clamp01(9.0) == 1.0
    assert When.Always(DfCtx()) == 1.0
    assert When.Never(DfCtx()) == 0.0


def test_FailAndFieldsPreserved() -> None:
    err = Df.Fail(reason={"reason": "invalid"}, payload={"node": "Root"})

    assert isinstance(err, Fail)
    assert err.Reason == {"reason": "invalid"}
    assert err.Payload == {"node": "Root"}


def PatrolNode(ctx: DfCtx) -> DfNode:
    _ = ctx
    yield Df.Act("Look")
    yield Df.Wait(1)
    yield Df.Succeed("done")


def test_AuthoringNodeShape() -> None:
    ctx = DfCtx()

    node = PatrolNode(ctx)
    typedNode = cast(DfNode, node)

    yielded = list(typedNode)

    assert yielded == [
        Act(Name="Look", Payload=None),
        Wait(Ticks=1),
        Succeed(Payload="done"),
    ]


def test_PushPopAuthoringShape() -> None:
    def StackNode(_ctx: DfCtx) -> DfNode:
        yield Df.Push("Combat")
        yield Df.Pop({"return": "idle"})

    yielded = list(StackNode(DfCtx()))
    assert yielded == [Push(Target="Combat"), Pop(Payload={"return": "idle"})]

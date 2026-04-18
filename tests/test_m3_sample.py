from __future__ import annotations

from pathlib import Path

from dreadfang.core import DfCtx
from dreadfang.runtime import DfActRecord, RunNode
from samples.PatrolRecoverSample import BuildRegistry, Root


def test_M3SamplePatrolOnlyFlowUsesYieldFromAndWait() -> None:
    ctx = DfCtx()

    result = RunNode(Root, ctx=ctx, registry=BuildRegistry())

    assert result.Status == "Succeeded"
    assert result.Tick == 1
    assert result.StepCount == 7
    assert result.Acts == (
        DfActRecord(Tick=0, Name="RootStart", Payload={"mode": "patrol"}),
        DfActRecord(Tick=0, Name="PatrolLook", Payload=None),
        DfActRecord(Tick=1, Name="PatrolStep", Payload={"lane": "north"}),
        DfActRecord(Tick=1, Name="TargetVisible", Payload=None),
        DfActRecord(Tick=1, Name="RootDone", Payload={"mode": "patrol"}),
    )


def test_M3SamplePushPopRecoverResumesParentAndMutatesState() -> None:
    ctx = DfCtx()
    ctx.State.Set("forceRecover", True)

    result = RunNode(Root, ctx=ctx, registry=BuildRegistry())

    assert result.Status == "Succeeded"
    assert result.Tick == 3
    assert tuple(record.Name for record in result.Acts) == (
        "RootStart",
        "PatrolLook",
        "PatrolStep",
        "TargetLost",
        "RecoverSweep",
        "RecoverLock",
        "RootDone",
    )
    assert result.Acts[4] == DfActRecord(Tick=1, Name="RecoverSweep", Payload={"attempt": 1})
    assert result.Acts[5] == DfActRecord(Tick=3, Name="RecoverLock", Payload=None)
    assert ctx.State.Get("recoverAttempts") == 1
    assert ctx.State.Get("mode") == "patrol"


def test_M3SampleSecondRecoverShowsFallbackBranch() -> None:
    ctx = DfCtx()
    ctx.State.Set("forceRecover", True)
    ctx.State.Set("recoverAttempts", 1)

    result = RunNode(Root, ctx=ctx, registry=BuildRegistry())

    assert result.Status == "Succeeded"
    assert result.Tick == 3
    assert tuple(record.Name for record in result.Acts)[-3:] == (
        "RecoverSweep",
        "RecoverFallback",
        "RootDone",
    )
    assert ctx.State.Get("recoverAttempts") == 2
    assert ctx.State.Get("mode") == "fallback"


def test_M3SampleLivesOutsideCorePackageBoundary() -> None:
    samplePath = Path(__file__).resolve().parents[1] / "samples" / "PatrolRecoverSample.py"

    assert samplePath.is_file()
    assert "dreadfang" not in samplePath.parts

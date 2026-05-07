from __future__ import annotations

from pathlib import Path

from dreadfang.core import DfCtx
from dreadfang.runtime import DfActRecord, DfActuatorRegistry, RunNode
from dreadfang.validator import ValidateFile
from samples.PatrolRecoverSample import BuildRegistry as BuildPatrolRegistry, Root as PatrolRoot
from samples.UtilityCommitmentSample import BuildRegistry as BuildUtilityRegistry, Root as UtilityRoot


def test_M7PatrolRecoverNodeModuleValidates() -> None:
    result = ValidateFile(Path("samples/PatrolRecoverNodes.py"))

    assert result.IsValid is True
    assert result.Diagnostics == ()


def test_M7UtilityCommitmentNodeModuleValidates() -> None:
    result = ValidateFile(Path("samples/UtilityCommitmentNodes.py"))

    assert result.IsValid is True
    assert result.Diagnostics == ()


def test_M7RuntimeWiringModuleIsOutsideSubsetAndFailsValidation() -> None:
    result = ValidateFile(Path("samples/UtilityCommitmentSample.py"))

    assert result.IsValid is False
    assert any(
        diagnostic.Message == "only module-level function definitions are allowed in Dreadfang authoring modules"
        for diagnostic in result.Diagnostics
    )


def test_M7NodeAndActuatorBoundaryRunTogether() -> None:
    records: list[str] = []
    actuators = DfActuatorRegistry()

    def CaptureSignal(act, _ctx):
        records.append(f"{act.Tick}:{act.Name}")

    actuators.Register("SignalObserved", CaptureSignal)

    ctx = DfCtx()
    ctx.State.Set("signalSeries", (0.75, 0.25))
    ctx.State.Set("hysteresis", 0.0)
    ctx.State.Set("minCommitTicks", 0)

    result = RunNode(UtilityRoot, ctx=ctx, registry=BuildUtilityRegistry(), actuators=actuators)

    assert result.Status == "Succeeded"
    assert result.Acts[:2] == (
        DfActRecord(Tick=0, Name="SignalObserved", Payload={"signal": 0.75}),
        DfActRecord(Tick=0, Name="TrackBeat", Payload=None),
    )
    assert records == ["0:SignalObserved", "1:SignalObserved"]


def test_M7ActStreamRecordsBeforeDispatch() -> None:
    actsSeenDuringDispatch: list[tuple[DfActRecord, ...]] = []

    def ObserveRecordedActs(act, ctx):
        history = ctx.State.Get("recordedActs", ())
        ctx.State.Set("recordedActs", (*history, act))
        actsSeenDuringDispatch.append(ctx.State.Get("recordedActs", ()))

    actuators = DfActuatorRegistry(Handlers={"RootStart": ObserveRecordedActs})
    result = RunNode(PatrolRoot, ctx=DfCtx(), registry=BuildPatrolRegistry(), actuators=actuators)

    assert result.Status == "Succeeded"
    assert len(result.Acts) >= 1
    assert actsSeenDuringDispatch[0][0].Name == "RootStart"

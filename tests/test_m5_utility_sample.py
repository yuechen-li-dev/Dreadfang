from __future__ import annotations

from pathlib import Path

from dreadfang.runtime import DfActRecord, DfDecisionRecord
from samples.UtilityCommitmentSample import RunUtilitySample, UtilitySampleConfig


def test_M5UtilitySampleRunsFromSampleFileAndShowsDecisions() -> None:
    config = UtilitySampleConfig(Hysteresis=0.0, MinCommitTicks=0)
    signalSeries = (0.52, 0.48, 0.51, 0.49, 0.52)

    outcome = RunUtilitySample(config=config, signalSeries=signalSeries)

    assert outcome.Result.Status == "Succeeded"
    assert outcome.Result.Tick == len(signalSeries)
    assert outcome.Result.Acts[0] == DfActRecord(Tick=0, Name="SignalObserved", Payload={"signal": 0.52})
    assert outcome.Result.Decisions[:2] == (
        DfDecisionRecord(Tick=0, Label="Track", Target="TrackBeat", Score=0.52),
        DfDecisionRecord(Tick=1, Label="Recover", Target="RecoverBeat", Score=0.52),
    )


def test_M5UtilitySampleHysteresisReducesSwitchingOnNoisySignal() -> None:
    signalSeries = (0.52, 0.48, 0.51, 0.49, 0.52, 0.48, 0.53)
    baseline = RunUtilitySample(
        config=UtilitySampleConfig(Hysteresis=0.0, MinCommitTicks=0),
        signalSeries=signalSeries,
    )
    stabilized = RunUtilitySample(
        config=UtilitySampleConfig(Hysteresis=0.05, MinCommitTicks=0),
        signalSeries=signalSeries,
    )

    assert baseline.SelectedLabels == ("Track", "Recover", "Track", "Recover", "Track", "Recover", "Track")
    assert baseline.SwitchCount == 6
    assert stabilized.SelectedLabels == ("Track", "Track", "Track", "Track", "Track", "Track", "Track")
    assert stabilized.SwitchCount == 0


def test_M5UtilitySampleMinCommitBlocksEarlySwitches() -> None:
    signalSeries = (0.70, 0.20, 0.20, 0.20)
    noCommit = RunUtilitySample(
        config=UtilitySampleConfig(Hysteresis=0.0, MinCommitTicks=0),
        signalSeries=signalSeries,
    )
    committed = RunUtilitySample(
        config=UtilitySampleConfig(Hysteresis=0.0, MinCommitTicks=2),
        signalSeries=signalSeries,
    )

    assert noCommit.SelectedLabels == ("Track", "Recover", "Recover", "Recover")
    assert committed.SelectedLabels == ("Track", "Track", "Track", "Recover")
    assert committed.Result.Decisions[1].Tick == 1
    assert committed.Result.Decisions[2].Tick == 2
    assert committed.Result.Decisions[3].Tick == 3


def test_M5UtilitySampleLivesOutsideCorePackageBoundary() -> None:
    samplePath = Path(__file__).resolve().parents[1] / "samples" / "UtilityCommitmentSample.py"

    assert samplePath.is_file()
    assert "dreadfang" not in samplePath.parts

from __future__ import annotations

from pathlib import Path

from dreadfang.adapters.story import Story, StoryOption
from dreadfang.core import Act, Await, Df, DfCtx, DfMessage
from dreadfang.runtime import DfActRecord, DfSession
from dreadfang.validator import ValidateFile
from samples.text_adventure.StoryRuntime import BuildStoryActuator, Choice, Root


def test_M17StoryLineAndSayProduceActs() -> None:
    assert Story.Line("fog") == Act(Name="Story.Line", Payload={"text": "fog"})
    assert Story.Say("Wiglaf", "ready") == Act(Name="Story.Say", Payload={"speaker": "Wiglaf", "text": "ready"})


def test_M17StoryOptionDataShape() -> None:
    option = Story.Option("stand", "Stand your ground")

    assert option == StoryOption(Key="stand", Label="Stand your ground")


def test_M17ChoiceEmitsPromptAwaitsAndStoresValidSelection() -> None:
    key = Df.Key("pick", str)
    ctx = DfCtx()
    choiceNode = Story.Choice(
        "Pick one",
        (Story.Option("left", "Left"), Story.Option("right", "Right")),
        StoreAs=key,
        ctx=ctx,
    )

    assert next(choiceNode) == Act(
        Name="Story.Choice",
        Payload={
            "prompt": "Pick one",
            "options": ({"key": "left", "label": "Left"}, {"key": "right", "label": "Right"}),
        },
    )
    assert next(choiceNode) == Await(Name="Story.Choice", TimeoutTicks=None)

    ctx.LastMessage = DfMessage("Story.Choice", "left")
    withStop = False
    try:
        next(choiceNode)
    except StopIteration:
        withStop = True

    assert withStop is True
    assert ctx.State.Get(key) == "left"


def test_M17StorySessionFlowAndInvalidChoiceFailure() -> None:
    logs: list[str] = []
    session = DfSession(NodeFactory=Root, Actuators=BuildStoryActuator(logs))

    waiting = session.RunUntilBlocked()
    assert waiting.Status == "Waiting"
    assert waiting.WaitingOn == "Story.Choice"
    assert waiting.Acts[:3] == (
        DfActRecord(Tick=0, Name="Story.Line", Payload={"text": "The barrow breathed smoke."}),
        DfActRecord(Tick=0, Name="Story.Say", Payload={"speaker": "Wiglaf", "text": "I will stand with you."}),
        DfActRecord(
            Tick=0,
            Name="Story.Choice",
            Payload={
                "prompt": "What do you do?",
                "options": (
                    {"key": "stand", "label": "Stand your ground"},
                    {"key": "call", "label": "Call to your men"},
                ),
            },
        ),
    )
    assert logs == [
        "The barrow breathed smoke.",
        "Wiglaf: I will stand with you.",
        "What do you do?",
    ]

    session.AddMessage(DfMessage("Story.Choice", "stand"))
    resumed = session.RunUntilBlocked()
    assert resumed.Status == "Steady"
    assert session.Ctx.State.Get(Choice) == "stand"
    assert resumed.Acts[-1] == DfActRecord(
        Tick=0,
        Name="Story.Line",
        Payload={"text": "You raise your shield and hold the ridge."},
    )

    badSession = DfSession(NodeFactory=Root)
    badSession.RunUntilBlocked()
    badSession.AddMessage(DfMessage("Story.Choice", "flee"))
    bad = badSession.RunUntilBlocked()
    assert bad.Status == "Failed"
    assert bad.FailureReason == "invalid Story.Choice payload"


def test_M17StoryNodesValidateAndRuntimeWiringRemainsOutsideSubset() -> None:
    nodeValidation = ValidateFile(Path("samples/text_adventure/StoryNodes.py"))
    runtimeValidation = ValidateFile(Path("samples/text_adventure/StoryRuntime.py"))

    assert nodeValidation.IsValid is True
    assert runtimeValidation.IsValid is False
    assert any(
        diagnostic.Message == "only module-level function definitions are allowed in Dreadfang authoring modules"
        for diagnostic in runtimeValidation.Diagnostics
    )

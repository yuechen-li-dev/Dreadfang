from __future__ import annotations

from pathlib import Path
from types import ModuleType

from dreadfang.adapters.story import Story
from dreadfang.core import Df, DfCtx, DfMessage
from dreadfang.runtime import DfActRecord, DfActuatorRegistry, DfRunResult, DfSession


def LoadNodesModule() -> ModuleType:
    module = ModuleType("StoryNodes")
    module.Df = Df
    module.Story = Story
    modulePath = Path(__file__).with_name("StoryNodes.py")
    sourceText = modulePath.read_text(encoding="utf-8")
    exec(sourceText, module.__dict__)
    return module


StoryNodes = LoadNodesModule()
Root = StoryNodes.Root
Choice = StoryNodes.Choice


def BuildStoryActuator(logs: list[str]) -> DfActuatorRegistry:
    actuators = DfActuatorRegistry()

    def HandleLine(act: DfActRecord, _ctx: DfCtx) -> None:
        payload = act.Payload if isinstance(act.Payload, dict) else {}
        logs.append(str(payload.get("text", "")))

    def HandleSay(act: DfActRecord, _ctx: DfCtx) -> None:
        payload = act.Payload if isinstance(act.Payload, dict) else {}
        logs.append(f"{payload.get('speaker', '')}: {payload.get('text', '')}")

    def HandleChoice(act: DfActRecord, _ctx: DfCtx) -> None:
        payload = act.Payload if isinstance(act.Payload, dict) else {}
        prompt = str(payload.get("prompt", ""))
        logs.append(prompt)

    actuators.Register("Story.Line", HandleLine)
    actuators.Register("Story.Say", HandleSay)
    actuators.Register("Story.Choice", HandleChoice)
    return actuators


def RunStorySession(session: DfSession, messagePayload: str | None = None) -> DfRunResult:
    if messagePayload is not None:
        session.AddMessage(DfMessage("Story.Choice", messagePayload))
    return session.RunUntilBlocked()

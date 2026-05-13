from __future__ import annotations

from dataclasses import dataclass
from typing import Generator, Iterable

from dreadfang.core import Df, DfCtx, DfKey, DfOp


@dataclass(frozen=True)
class StoryOption:
    Key: str
    Label: str


class Story:
    @staticmethod
    def Line(text: str) -> DfOp:
        return Df.Act("Story.Line", {"text": text})

    @staticmethod
    def Say(speaker: str, text: str) -> DfOp:
        return Df.Act("Story.Say", {"speaker": speaker, "text": text})

    @staticmethod
    def Option(key: str, label: str) -> StoryOption:
        return StoryOption(Key=key, Label=label)

    @staticmethod
    def Choice(prompt: str, options: Iterable[StoryOption], StoreAs: DfKey[str], ctx: DfCtx) -> Generator[DfOp, None, None]:
        normalizedOptions = tuple(options)
        payload = {
            "prompt": prompt,
            "options": tuple({"key": option.Key, "label": option.Label} for option in normalizedOptions),
        }
        yield Df.Act("Story.Choice", payload)
        yield Df.Await("Story.Choice")
        if ctx.LastMessage is None:
            yield Df.Fail("Story.Choice awaited but no message was delivered")
            return
        selected = ctx.LastMessage.Payload
        allowed = tuple(option.Key for option in normalizedOptions)
        if not isinstance(selected, str) or selected not in allowed:
            yield Df.Fail("invalid Story.Choice payload", {"received": selected, "allowed": allowed})
            return
        ctx.State.Set(StoreAs, selected)

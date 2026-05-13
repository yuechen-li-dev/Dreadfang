from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Generator, Generic, Iterable, TypeAlias, TypeVar


TValue = TypeVar("TValue")


@dataclass(frozen=True)
class DfKey(Generic[TValue]):
    Name: str
    ValueType: type[TValue]


class DfOp:
    """Marker base type for all Dreadfang operations."""


DfNode: TypeAlias = Generator[DfOp, None, None]
DfScorer: TypeAlias = Callable[["DfCtx"], float]


@dataclass
class DfState:
    """Small explicit state bag for authored nodes."""

    _values: dict[str, object] = field(default_factory=dict)
    _keyTypes: dict[str, type[object]] = field(default_factory=dict)

    def Get(self, key: str | DfKey[TValue], default: TValue | None = None) -> object | TValue | None:
        if isinstance(key, DfKey):
            self._RegisterTypedKey(key)
            if default is not None:
                self._ValidateType(key.Name, key.ValueType, default, "default")
            return self._values.get(key.Name, default)
        return self._values.get(key, default)

    def Set(self, key: str | DfKey[TValue], value: object) -> None:
        if isinstance(key, DfKey):
            self._RegisterTypedKey(key)
            self._ValidateType(key.Name, key.ValueType, value, "value")
            self._values[key.Name] = value
            return
        self._values[key] = value

    def _RegisterTypedKey(self, key: DfKey[object]) -> None:
        existingType = self._keyTypes.get(key.Name)
        if existingType is None:
            self._keyTypes[key.Name] = key.ValueType
            return
        if existingType is not key.ValueType:
            raise TypeError(
                f"State key '{key.Name}' already registered with type "
                f"{existingType.__name__}, cannot use {key.ValueType.__name__}"
            )

    def _ValidateType(self, keyName: str, expectedType: type[object], value: object, valueLabel: str) -> None:
        if type(value) is not expectedType:
            raise TypeError(
                f"State key '{keyName}' expects {expectedType.__name__} {valueLabel}, "
                f"got {type(value).__name__}"
            )


@dataclass
class DfCtx:
    """Tiny execution context visible to authored nodes."""

    State: DfState = field(default_factory=DfState)
    Mailbox: list[object] = field(default_factory=list)
    Tick: int = 0


@dataclass(frozen=True)
class Push(DfOp):
    Target: str


@dataclass(frozen=True)
class Pop(DfOp):
    Payload: object | None = None


@dataclass(frozen=True)
class Succeed(DfOp):
    Payload: object | None = None


@dataclass(frozen=True)
class Fail(DfOp):
    Reason: object | None = None
    Payload: object | None = None


@dataclass(frozen=True)
class Wait(DfOp):
    Ticks: int = 1


@dataclass(frozen=True)
class Until(DfOp):
    Predicate: Callable[[DfCtx], bool]


@dataclass(frozen=True)
class Act(DfOp):
    Name: str
    Payload: object | None = None


@dataclass(frozen=True)
class Event(DfOp):
    Name: str
    Payload: object | None = None


@dataclass(frozen=True)
class Await(DfOp):
    Name: str
    TimeoutTicks: int | None = None


@dataclass(frozen=True)
class Option(DfOp):
    Label: str
    Score: DfScorer
    Target: str


@dataclass(frozen=True)
class Decide(DfOp):
    Options: tuple[Option, ...]
    Hysteresis: float = 0.0
    MinCommitTicks: int = 0


def Clamp01(value: float) -> float:
    if value < 0.0:
        return 0.0
    if value > 1.0:
        return 1.0
    return value


class When:
    @staticmethod
    def Always(_ctx: DfCtx) -> float:
        return 1.0

    @staticmethod
    def Never(_ctx: DfCtx) -> float:
        return 0.0


class Df:
    """Small helper namespace for authoring Dreadfang ops."""

    @staticmethod
    def Push(target: str) -> Push:
        return Push(Target=target)

    @staticmethod
    def Pop(payload: object | None = None) -> Pop:
        return Pop(Payload=payload)

    @staticmethod
    def Succeed(payload: object | None = None) -> Succeed:
        return Succeed(Payload=payload)

    @staticmethod
    def Fail(reason: object | None = None, payload: object | None = None) -> Fail:
        return Fail(Reason=reason, Payload=payload)

    @staticmethod
    def Wait(ticks: int = 1) -> Wait:
        return Wait(Ticks=ticks)

    @staticmethod
    def Until(predicate: Callable[[DfCtx], bool]) -> Until:
        return Until(Predicate=predicate)

    @staticmethod
    def Act(name: str, payload: object | None = None) -> Act:
        return Act(Name=name, Payload=payload)

    @staticmethod
    def Event(name: str, payload: object | None = None) -> Event:
        return Event(Name=name, Payload=payload)

    @staticmethod
    def Await(name: str, timeoutTicks: int | None = None) -> Await:
        return Await(Name=name, TimeoutTicks=timeoutTicks)

    @staticmethod
    def Option(
        label: str,
        score: DfScorer,
        target: str,
    ) -> Option:
        return Option(Label=label, Score=score, Target=target)

    @staticmethod
    def Decide(
        *options: Option | Iterable[Option],
        hysteresis: float = 0.0,
        min_commit_ticks: int = 0,
    ) -> Decide:
        normalized: list[Option] = []
        for candidate in options:
            if isinstance(candidate, Option):
                normalized.append(candidate)
            else:
                normalized.extend(candidate)
        return Decide(
            Options=tuple(normalized),
            Hysteresis=hysteresis,
            MinCommitTicks=min_commit_ticks,
        )
    @staticmethod
    def Key(name: str, valueType: type[TValue]) -> DfKey[TValue]:
        return DfKey(Name=name, ValueType=valueType)

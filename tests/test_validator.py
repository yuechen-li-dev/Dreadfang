from __future__ import annotations

from pathlib import Path

from dreadfang.validator import ValidateFile, ValidateSource


def test_ValidateSourceAcceptsSimpleNodeAuthoring() -> None:
    source = '''
def PatrolNode(ctx):
    yield Df.Act("Look")
    if ctx.Tick > 0:
        yield Df.Wait(1)
    yield Df.Succeed()
'''

    result = ValidateSource(source)

    assert result.IsValid is True
    assert result.Diagnostics == ()


def test_ValidateSourceAcceptsHelperAndRestrictedYieldFrom() -> None:
    source = '''
def ChildNode(ctx):
    yield Df.Act("Child")


def ParentNode(ctx):
    yield Df.Act("Parent")
    yield from ChildNode(ctx)
    yield Df.Succeed()
'''

    result = ValidateSource(source)

    assert result.IsValid is True
    assert result.Diagnostics == ()


def test_ValidateSourceRejectsArbitraryImport() -> None:
    source = '''
import random


def Node(ctx):
    yield Df.Succeed()
'''

    result = ValidateSource(source)

    assert result.IsValid is False
    assert result.Diagnostics[0].Message == "only module-level function definitions are allowed in Dreadfang authoring modules"


def test_ValidateSourceRejectsDisallowedConstructs() -> None:
    source = '''
class Bad:
    pass


@Decorator
def Node(ctx):
    global X
    try:
        value = lambda x: x
    except Exception:
        raise
    return value
'''

    result = ValidateSource(source)

    assert result.IsValid is False
    messages = tuple(diagnostic.Message for diagnostic in result.Diagnostics)
    assert "only module-level function definitions are allowed in Dreadfang authoring modules" in messages
    assert "decorators are not allowed in Dreadfang authoring modules" in messages
    assert "global is not allowed in Dreadfang authoring code" in messages
    assert "try/except is not allowed in Dreadfang authoring code" in messages


def test_ValidateSourceRejectsArbitraryCallAndYieldFrom() -> None:
    source = '''
def OtherNode(ctx):
    yield Df.Succeed()


def Node(ctx):
    random.random()
    yield from OtherModule.ChildNode(ctx)
    yield Df.Succeed()
'''

    result = ValidateSource(source)

    assert result.IsValid is False
    messages = tuple(diagnostic.Message for diagnostic in result.Diagnostics)
    assert "call target is not in the allowed Dreadfang subset" in messages
    assert "yield from is only allowed when delegating to a module-defined Dreadfang function" in messages


def test_ValidateSourceReportsDeterministicOrderAndCoordinates() -> None:
    source = '''
def Node(ctx):
    nonlocal value
    raise ValueError("bad")
'''

    result = ValidateSource(source)

    assert result.IsValid is False
    assert result.Diagnostics[0].Message == "nonlocal is not allowed in Dreadfang authoring code"
    assert result.Diagnostics[0].Line == 3
    assert result.Diagnostics[1].Message == "raise is not allowed in Dreadfang authoring code"
    assert result.Diagnostics[1].Line == 4


def test_ValidateFileReadsFromPath(tmp_path: Path) -> None:
    sourcePath = tmp_path / "node_module.py"
    sourcePath.write_text(
        '''
def Node(ctx):
    yield Df.Act("Look")
    yield Df.Succeed()
''',
        encoding="utf-8",
    )

    result = ValidateFile(sourcePath)

    assert result.IsValid is True
    assert result.Diagnostics == ()

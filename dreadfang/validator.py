from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path

_ALLOWED_DF_CALLS: frozenset[str] = frozenset(
    {
        "Act",
        "Await",
        "Decide",
        "Event",
        "Fail",
        "Option",
        "Pop",
        "Push",
        "Succeed",
        "Until",
        "Wait",
    }
)
_ALLOWED_BUILTIN_CALLS: frozenset[str] = frozenset({"bool", "float", "int", "len", "str"})
_ALLOWED_BINARY_OPERATORS: tuple[type[ast.operator], ...] = (
    ast.Add,
    ast.Sub,
    ast.Mult,
    ast.Div,
    ast.FloorDiv,
    ast.Mod,
)
_ALLOWED_UNARY_OPERATORS: tuple[type[ast.unaryop], ...] = (ast.Not, ast.UAdd, ast.USub)
_ALLOWED_COMPARE_OPERATORS: tuple[type[ast.cmpop], ...] = (
    ast.Eq,
    ast.NotEq,
    ast.Lt,
    ast.LtE,
    ast.Gt,
    ast.GtE,
    ast.Is,
    ast.IsNot,
    ast.In,
    ast.NotIn,
)


@dataclass(frozen=True)
class DfValidationDiagnostic:
    Message: str
    Line: int
    Column: int


@dataclass(frozen=True)
class DfValidationResult:
    IsValid: bool
    Diagnostics: tuple[DfValidationDiagnostic, ...]


def ValidateSource(sourceText: str, filename: str = "<memory>") -> DfValidationResult:
    try:
        module = ast.parse(sourceText, filename=filename)
    except SyntaxError as error:
        line = error.lineno or 1
        column = error.offset or 0
        return DfValidationResult(
            IsValid=False,
            Diagnostics=(
                DfValidationDiagnostic(
                    Message=f"syntax error: {error.msg}",
                    Line=line,
                    Column=column,
                ),
            ),
        )

    validator = _RestrictedSubsetValidator(module)
    diagnostics = validator.Validate()
    return DfValidationResult(IsValid=len(diagnostics) == 0, Diagnostics=tuple(diagnostics))


def ValidateFile(path: str | Path) -> DfValidationResult:
    sourcePath = Path(path)
    sourceText = sourcePath.read_text(encoding="utf-8")
    return ValidateSource(sourceText, filename=str(sourcePath))


class _RestrictedSubsetValidator(ast.NodeVisitor):
    def __init__(self, module: ast.Module) -> None:
        self._module = module
        self._diagnostics: list[DfValidationDiagnostic] = []
        self._moduleFunctionNames = {
            statement.name
            for statement in module.body
            if isinstance(statement, ast.FunctionDef)
        }

    def Validate(self) -> list[DfValidationDiagnostic]:
        self.VisitModule(self._module)
        return self._diagnostics

    def VisitModule(self, node: ast.Module) -> None:
        for index, statement in enumerate(node.body):
            if (
                index == 0
                and isinstance(statement, ast.Expr)
                and isinstance(statement.value, ast.Constant)
                and isinstance(statement.value.value, str)
            ):
                continue

            if isinstance(statement, ast.FunctionDef):
                self._VisitFunctionDef(statement)
                continue

            self._Reject(
                statement,
                "only module-level function definitions are allowed in Dreadfang authoring modules",
            )

    def _VisitFunctionDef(self, node: ast.FunctionDef) -> None:
        if node.decorator_list:
            self._Reject(node, "decorators are not allowed in Dreadfang authoring modules")

        if node.returns is not None:
            self._VisitExpression(node.returns)

        self._ValidateArguments(node.args)

        for statement in node.body:
            self._VisitStatement(statement)

    def _ValidateArguments(self, args: ast.arguments) -> None:
        for expression in args.defaults:
            self._VisitExpression(expression)

        for expression in args.kw_defaults:
            if expression is not None:
                self._VisitExpression(expression)

        allArguments = [*args.posonlyargs, *args.args, *args.kwonlyargs]
        for argument in allArguments:
            if argument.annotation is not None:
                self._VisitExpression(argument.annotation)

        if args.vararg is not None:
            self._Reject(args.vararg, "varargs are not allowed in Dreadfang authoring functions")

        if args.kwarg is not None:
            self._Reject(args.kwarg, "keyword varargs are not allowed in Dreadfang authoring functions")

    def _VisitStatement(self, node: ast.stmt) -> None:
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            self._Reject(node, "imports are restricted to approved Dreadfang modules")
            return

        if isinstance(node, ast.ClassDef):
            self._Reject(node, "class definitions are not allowed in Dreadfang authoring modules")
            return

        if isinstance(node, (ast.AsyncFunctionDef, ast.AsyncFor, ast.AsyncWith, ast.Await)):
            self._Reject(node, "async features are not allowed in Dreadfang authoring modules")
            return

        if isinstance(node, ast.Try):
            self._Reject(node, "try/except is not allowed in Dreadfang authoring code")
            return

        if isinstance(node, ast.Raise):
            self._Reject(node, "raise is not allowed in Dreadfang authoring code")
            return

        if isinstance(node, ast.Global):
            self._Reject(node, "global is not allowed in Dreadfang authoring code")
            return

        if isinstance(node, ast.Nonlocal):
            self._Reject(node, "nonlocal is not allowed in Dreadfang authoring code")
            return

        if isinstance(node, ast.FunctionDef):
            self._Reject(node, "nested function definitions are not allowed")
            return

        if isinstance(node, ast.If):
            self._VisitExpression(node.test)
            for child in node.body:
                self._VisitStatement(child)
            for child in node.orelse:
                self._VisitStatement(child)
            return

        if isinstance(node, ast.Assign):
            for target in node.targets:
                self._VisitAssignmentTarget(target)
            self._VisitExpression(node.value)
            return

        if isinstance(node, ast.AnnAssign):
            if node.value is None:
                self._Reject(node, "annotated assignment must include a value")
                return
            self._VisitAssignmentTarget(node.target)
            self._VisitExpression(node.annotation)
            self._VisitExpression(node.value)
            return

        if isinstance(node, ast.Return):
            if node.value is not None:
                self._VisitExpression(node.value)
            return

        if isinstance(node, ast.Expr):
            self._VisitExpression(node.value)
            return

        if isinstance(node, ast.Pass):
            return

        self._Reject(
            node,
            f"{type(node).__name__} statements are not allowed in Dreadfang authoring code",
        )

    def _VisitAssignmentTarget(self, node: ast.expr) -> None:
        if isinstance(node, ast.Name):
            return

        if isinstance(node, ast.Attribute):
            self._VisitExpression(node.value)
            return

        if isinstance(node, ast.Subscript):
            self._VisitExpression(node.value)
            self._VisitExpression(node.slice)
            return

        self._Reject(node, "assignment target is not in the allowed Dreadfang subset")

    def _VisitExpression(self, node: ast.expr) -> None:
        if isinstance(node, ast.Constant):
            return

        if isinstance(node, ast.Name):
            return

        if isinstance(node, ast.Attribute):
            self._VisitExpression(node.value)
            return

        if isinstance(node, ast.BoolOp):
            for value in node.values:
                self._VisitExpression(value)
            return

        if isinstance(node, ast.BinOp):
            self._VisitExpression(node.left)
            self._VisitExpression(node.right)
            if not isinstance(node.op, _ALLOWED_BINARY_OPERATORS):
                self._Reject(node, f"operator {type(node.op).__name__} is not allowed")
            return

        if isinstance(node, ast.UnaryOp):
            self._VisitExpression(node.operand)
            if not isinstance(node.op, _ALLOWED_UNARY_OPERATORS):
                self._Reject(node, f"operator {type(node.op).__name__} is not allowed")
            return

        if isinstance(node, ast.Compare):
            self._VisitExpression(node.left)
            for comparator in node.comparators:
                self._VisitExpression(comparator)
            for operator in node.ops:
                if not isinstance(operator, _ALLOWED_COMPARE_OPERATORS):
                    self._Reject(node, f"comparison operator {type(operator).__name__} is not allowed")
            return

        if isinstance(node, ast.IfExp):
            self._VisitExpression(node.test)
            self._VisitExpression(node.body)
            self._VisitExpression(node.orelse)
            return

        if isinstance(node, ast.Dict):
            for key in node.keys:
                if key is not None:
                    self._VisitExpression(key)
            for value in node.values:
                self._VisitExpression(value)
            return

        if isinstance(node, ast.Tuple):
            for element in node.elts:
                self._VisitExpression(element)
            return

        if isinstance(node, ast.List):
            for element in node.elts:
                self._VisitExpression(element)
            return

        if isinstance(node, ast.Subscript):
            self._VisitExpression(node.value)
            self._VisitExpression(node.slice)
            return

        if isinstance(node, ast.Call):
            self._VisitCall(node)
            return

        if isinstance(node, ast.Yield):
            if node.value is not None:
                self._VisitExpression(node.value)
            return

        if isinstance(node, ast.YieldFrom):
            self._VisitYieldFrom(node)
            return

        if isinstance(node, ast.Lambda):
            self._Reject(node, "lambda is not allowed in Dreadfang authoring modules")
            return

        if isinstance(node, (ast.ListComp, ast.DictComp, ast.SetComp, ast.GeneratorExp)):
            self._Reject(node, "comprehensions are not allowed in Dreadfang authoring modules")
            return

        if isinstance(node, ast.NamedExpr):
            self._Reject(node, "assignment expressions are not allowed")
            return

        self._Reject(
            node,
            f"expression node {type(node).__name__} is not in the allowed Dreadfang subset",
        )

    def _VisitCall(self, node: ast.Call) -> None:
        for argument in node.args:
            self._VisitExpression(argument)
        for keyword in node.keywords:
            self._VisitExpression(keyword.value)

        if self._IsAllowedCallTarget(node.func):
            return

        self._Reject(node, "call target is not in the allowed Dreadfang subset")

    def _VisitYieldFrom(self, node: ast.YieldFrom) -> None:
        if isinstance(node.value, ast.Call) and isinstance(node.value.func, ast.Name):
            calledName = node.value.func.id
            if calledName in self._moduleFunctionNames:
                self._VisitCall(node.value)
                return

        self._Reject(
            node,
            "yield from is only allowed when delegating to a module-defined Dreadfang function",
        )

    def _IsAllowedCallTarget(self, node: ast.expr) -> bool:
        if isinstance(node, ast.Name):
            if node.id in self._moduleFunctionNames:
                return True
            if node.id in _ALLOWED_BUILTIN_CALLS:
                return True
            return False

        if isinstance(node, ast.Attribute):
            if isinstance(node.value, ast.Name) and node.value.id == "Df" and node.attr in _ALLOWED_DF_CALLS:
                return True

            if node.attr in {"Get", "Set"} and isinstance(node.value, ast.Attribute):
                return node.value.attr == "State"

        return False

    def _Reject(self, node: ast.AST, message: str) -> None:
        self._diagnostics.append(
            DfValidationDiagnostic(
                Message=message,
                Line=getattr(node, "lineno", 1),
                Column=getattr(node, "col_offset", 0),
            )
        )

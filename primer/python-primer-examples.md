document:
  name: python-primer-examples
  format: toon
  version: 1

intent:
  summary:
    Provide small example pairs that demonstrate the allowed Python subset in practice.
    These examples are normative anchors for authors.
  audience:
    primary:
      LLM authors
    secondary:
      human contributors
    additional:
      notebook users moving exploratory logic into maintainable modules

examples:
  typing:
    summary:
      Public types should be explicit and useful.

    good_typed_public_function:
      why:
        The function signature makes inputs and outputs obvious before runtime.
      code: |
        from pathlib import Path

        def read_text_file(path: Path) -> str:
            return path.read_text(encoding="utf-8")

    good_typed_module_boundary:
      why:
        The boundary shape is clear and the caller does not need to guess what comes back.
      code: |
        from dataclasses import dataclass

        @dataclass(frozen=True)
        class UserRecord:
            user_id: str
            display_name: str
            is_active: bool

        def parse_user_record(raw: dict[str, object]) -> UserRecord:
            return UserRecord(
                user_id=str(raw["user_id"]),
                display_name=str(raw["display_name"]),
                is_active=bool(raw["is_active"]),
            )

    bad_untyped_public_function:
      why:
        The caller has to infer too much from implementation details or trial and error.
      code: |
        def read_text_file(path):
            return open(path).read()

    bad_any_heavy_design:
      why:
        Any removes useful guarantees and lets ambiguity spread through the codebase.
      code: |
        from typing import Any

        def process_payload(payload: dict[str, Any]) -> Any:
            return payload.get("result")

    good_protocol_boundary:
      why:
        Structural typing gives a clean behavioral boundary without forcing inheritance-heavy design.
      code: |
        from typing import Protocol

        class TextWriter(Protocol):
            def write(self, text: str) -> None:
                ...

        def emit_report(writer: TextWriter, text: str) -> None:
            writer.write(text)

    bad_abc_for_small_structural_need:
      why:
        Inheritance machinery is used where a simple behavioral protocol would be lighter and clearer.
      code: |
        from abc import ABC, abstractmethod

        class TextWriterBase(ABC):
            @abstractmethod
            def write(self, text: str) -> None:
                raise NotImplementedError

  data_shape:
    summary:
      Data shape must be obvious inside core logic.

    good_dataclass_record:
      why:
        Named typed fields make structure explicit and easy to review.
      code: |
        from dataclasses import dataclass

        @dataclass(frozen=True)
        class BuildConfig:
            output_dir: str
            optimize: bool
            max_workers: int

        def describe_build(config: BuildConfig) -> str:
            mode = "optimized" if config.optimize else "debug"
            return f"{mode} build -> {config.output_dir} ({config.max_workers} workers)"

    good_normalize_boundary_data_early:
      why:
        Loose external data is normalized once, then the rest of the code can stay clean.
      code: |
        from dataclasses import dataclass

        @dataclass(frozen=True)
        class Point2D:
            x: float
            y: float

        def parse_point(raw: dict[str, object]) -> Point2D:
            return Point2D(
                x=float(raw["x"]),
                y=float(raw["y"]),
            )

        def distance_from_origin(point: Point2D) -> float:
            return (point.x ** 2 + point.y ** 2) ** 0.5

    bad_nested_dict_soup:
      why:
        Reviewers must remember undocumented keys and shapes throughout the call chain.
      code: |
        def distance_from_origin(data):
            return (data["point"]["coords"]["x"] ** 2 + data["point"]["coords"]["y"] ** 2) ** 0.5

    bad_mystery_tuple:
      why:
        Positional structure is harder to read and easier to misuse than named fields.
      code: |
        def load_user():
            return ("u123", "Alice", True)

        user = load_user()
        print(user[1])
    
    good_dataclass_post_init_validation:
      why:
        The type enforces a real invariant directly and locally.
      code: |
        from dataclasses import dataclass

        @dataclass(frozen=True)
        class PortNumber:
            value: int

            def __post_init__(self) -> None:
                if not (0 < self.value < 65536):
                    raise ValueError("port must be between 1 and 65535")

    bad_dataclass_hidden_framework_behavior:
      why:
        The dataclass now performs too much hidden lifecycle work for an ordinary record type.
      code: |
        from dataclasses import dataclass

        @dataclass
        class UserConfig:
            path: str

            def __post_init__(self) -> None:
                self._raw = load_global_state()
                self._session = connect_to_service(self.path)
                self._register_everything()

  functions_first:
    summary:
      Python is function-first by default.

    good_plain_functions:
      why:
        Simple behavior stays simple and does not need class theater.
      code: |
        from dataclasses import dataclass

        @dataclass(frozen=True)
        class Rectangle:
            width: float
            height: float

        def area(rectangle: Rectangle) -> float:
            return rectangle.width * rectangle.height

        def perimeter(rectangle: Rectangle) -> float:
            return 2.0 * (rectangle.width + rectangle.height)

    good_small_stateful_class_when_justified:
      why:
        A class is acceptable when it owns real state and has a clear lifecycle.
      code: |
        class LineReader:
            def __init__(self, path: str) -> None:
                self._path = path
                self._handle = open(path, "r", encoding="utf-8")

            def read_line(self) -> str:
                return self._handle.readline()

            def close(self) -> None:
                self._handle.close()

    bad_namespace_class:
      why:
        This is just a function wearing a fake mustache.
      code: |
        class MathUtils:
            def area(self, width: float, height: float) -> float:
                return width * height

            def perimeter(self, width: float, height: float) -> float:
                return 2.0 * (width + height)

    bad_fake_architecture:
      why:
        Manager/service/controller naming does not create real structure.
      code: |
        class RectangleService:
            def __init__(self) -> None:
                self._helper = RectangleHelper()

            def handle_rectangle(self, width: float, height: float) -> float:
                return self._helper.compute(width, height)

        class RectangleHelper:
            def compute(self, width: float, height: float) -> float:
                return width * height

  defaults_and_signatures:
    summary:
      Function defaults must not smuggle shared mutable state across calls.

    good_none_default:
      why:
        A fresh list is created when needed, so calls do not share hidden state.
      code: |
        def append_name(name: str, names: list[str] | None = None) -> list[str]:
            if names is None:
                names = []
            names.append(name)
            return names

    bad_mutable_default:
      why:
        State persists across calls in a way that looks innocent and behaves haunted.
      code: |
        def append_name(name: str, names: list[str] = []) -> list[str]:
            names.append(name)
            return names

  exceptions:
    summary:
      Exceptions are allowed, but failure must remain disciplined and visible.

    good_narrow_exception_handling:
      why:
        The code catches a specific failure and handles it honestly.
      code: |
        import json
        from pathlib import Path

        def load_json_file(path: Path) -> dict[str, object]:
            try:
                text = path.read_text(encoding="utf-8")
            except FileNotFoundError as exc:
                raise FileNotFoundError(f"missing config file: {path}") from exc

            return json.loads(text)

    good_explicit_validation_error:
      why:
        The function raises a clear exception for invalid input instead of pretending everything is fine.
      code: |
        def parse_positive_int(text: str) -> int:
            if not text:
                raise ValueError("input is empty")

            value = int(text)
            if value <= 0:
                raise ValueError("value must be positive")

            return value

    bad_bare_except:
      why:
        Bare except hides the real problem and catches too much.
      code: |
        def load_json_file(path):
            try:
                return json.loads(open(path).read())
            except:
                return {}

    bad_silent_swallow:
      why:
        Failure disappears and the caller receives misleading output.
      code: |
        def parse_positive_int(text: str) -> int:
            try:
                return int(text)
            except ValueError:
                return 0

    bad_logging_instead_of_handling:
      why:
        Logging does not make failure honest or testable by itself.
      code: |
        import logging

        def load_config(path: str) -> dict[str, object]:
            try:
                with open(path, "r", encoding="utf-8") as handle:
                    return {"text": handle.read()}
            except OSError:
                logging.warning("could not load config")
                return {}

  decorators:
    summary:
      Decorators may simplify code, but may not hide behavior.

    good_simple_decorator:
      why:
        The decorator's behavior is small, explicit, and unsurprising.
      code: |
        from functools import wraps
        from time import perf_counter
        from typing import Callable, TypeVar

        T = TypeVar("T")

        def timed(func: Callable[..., T]) -> Callable[..., T]:
            @wraps(func)
            def wrapper(*args, **kwargs):
                start = perf_counter()
                result = func(*args, **kwargs)
                end = perf_counter()
                print(f"{func.__name__} took {end - start:.3f}s")
                return result

            return wrapper

    bad_behavior_hiding_stack:
      why:
        Important behavior is now spread across decorators instead of visible in the function body.
      code: |
        @retry(times=5)
        @cached(ttl=300)
        @register("daily_report")
        @audit_action("report_run")
        def run_daily_report(user_id: str) -> dict[str, object]:
            return generate_report(user_id)

    bad_registration_magic:
      why:
        Import order now changes behavior and the module performs hidden side effects.
      code: |
        REGISTRY = {}

        def register(name):
            def decorator(func):
                REGISTRY[name] = func
                return func
            return decorator

        @register("compress")
        def compress_file(path: str) -> bytes:
            with open(path, "rb") as handle:
                return handle.read()

  side_effects_and_state:
    summary:
      Side effects should be visible and controlled.

    good_explicit_dependency_passing:
      why:
        The function says what it depends on instead of pulling state from nowhere.
      code: |
        from dataclasses import dataclass

        @dataclass(frozen=True)
        class AppConfig:
            output_dir: str
            dry_run: bool

        def write_report(config: AppConfig, report_text: str) -> None:
            if config.dry_run:
                return

            path = f"{config.output_dir}/report.txt"
            with open(path, "w", encoding="utf-8") as handle:
                handle.write(report_text)

    good_boundary_io:
      why:
        I/O happens at a visible boundary, not buried deep in utility code.
      code: |
        def build_report(name: str, score: int) -> str:
            return f"{name}: {score}"

        def save_report(path: str, report_text: str) -> None:
            with open(path, "w", encoding="utf-8") as handle:
                handle.write(report_text)

    bad_hidden_global_state:
      why:
        The function depends on ambient mutable state that is easy to forget and hard to test.
      code: |
        CURRENT_OUTPUT_DIR = "out"

        def write_report(report_text: str) -> None:
            with open(f"{CURRENT_OUTPUT_DIR}/report.txt", "w", encoding="utf-8") as handle:
                handle.write(report_text)

    bad_import_time_work:
      why:
        Merely importing the module now triggers side effects.
      code: |
        import requests

        REMOTE_SCHEMA = requests.get("https://example.com/schema.json", timeout=5).json()

  modules_and_imports:
    summary:
      Modules should stay focused and predictable.

    good_focused_module:
      why:
        The module has a clear job and minimal import-time behavior.
      code: |
        from dataclasses import dataclass

        @dataclass(frozen=True)
        class Token:
            kind: str
            text: str

        def lex_word(text: str) -> Token:
            return Token(kind="word", text=text.strip())

    bad_junk_drawer_module:
      why:
        Unrelated helpers accumulate until the module stops meaning anything.
      code: |
        import json
        import os
        import random
        import requests
        import subprocess

        GLOBAL_CACHE = {}

        def parse_config(text):
            return json.loads(text)

        def restart_machine():
            subprocess.run(["shutdown", "/r"])

        def random_name():
            return random.choice(["a", "b", "c"])

        def fetch_data(url):
            return requests.get(url).json()

  dependencies:
    summary:
      Prefer boring dependencies.

    good_stdlib_first:
      why:
        The standard library already solves the problem clearly.
      code: |
        from pathlib import Path

        def list_python_files(root: Path) -> list[Path]:
            return [path for path in root.rglob("*.py") if path.is_file()]

    bad_dependency_for_trivial_problem:
      why:
        A package is added for behavior that ordinary Python handles just fine.
      code: |
        import some_super_path_lib

        def list_python_files(root):
            return some_super_path_lib.deep_scan(root, pattern="*.py")

  comprehensions_and_expressions:
    summary:
      Short expressions are fine. Puzzle code is not.

    good_simple_comprehension:
      why:
        The logic is short and the shape is obvious.
      code: |
        def active_user_names(users: list[dict[str, object]]) -> list[str]:
            return [str(user["name"]) for user in users if bool(user["is_active"])]

    good_named_intermediate_values:
      why:
        Breaking steps apart makes the behavior easier to inspect.
      code: |
        def summarize_scores(scores: list[int]) -> dict[str, float]:
            count = len(scores)
            total = sum(scores)
            average = total / count if count else 0.0

            return {
                "count": float(count),
                "total": float(total),
                "average": average,
            }

    bad_expression_soup:
      why:
        Several operations are compressed together until the intent becomes muddy.
      code: |
        def summarize_scores(scores):
            return {"count": len(scores), "total": sum(scores), "average": (sum(scores) / len(scores) if scores else 0.0)}

    bad_business_logic_in_lambda:
      why:
        Important logic is harder to read and debug when buried in anonymous expressions.
      code: |
        sorted_users = sorted(
            users,
            key=lambda user: (0 if user["is_admin"] else 1, user["last_name"].strip().lower(), user["first_name"].strip().lower()),
        )

  notebooks:
    summary:
      Notebooks are for exploration and orchestration, not permanent architecture.

    good_notebook_calls_module:
      why:
        The notebook stays thin while stable logic lives in testable modules.
      code: |
        # notebook cell
        from analysis.metrics import summarize_scores
        from analysis.io import load_scores_csv

        scores = load_scores_csv("scores.csv")
        summary = summarize_scores(scores)
        summary

    good_module_extracted_from_notebook:
      why:
        Stable logic can now be imported, tested, and reused.
      code: |
        # analysis/metrics.py
        def summarize_scores(scores: list[int]) -> dict[str, float]:
            count = len(scores)
            total = sum(scores)
            average = total / count if count else 0.0

            return {
                "count": float(count),
                "total": float(total),
                "average": average,
            }

    bad_notebook_business_logic_pile:
      why:
        State, I/O, transformation, and reporting are all mixed in one place and depend on execution order.
      code: |
        # notebook cell
        import pandas as pd

        if "df" not in globals():
            df = pd.read_csv("scores.csv")

        df = df[df["active"] == True]
        df["normalized"] = df["score"].apply(lambda x: x / 100.0 if x > 0 else 0.0)
        result = df.groupby("team").agg({"normalized": "mean"}).reset_index()
        print(result)

    bad_hidden_notebook_state:
      why:
        The cell only works if other cells were already run in the right order.
      code: |
        # notebook cell
        filtered = raw_df[raw_df["kind"] == selected_kind]
        chart(filtered)

  pandas_and_data_tools:
    summary:
      Heavy data tools are acceptable when justified, but they should not replace explicit design.

    good_pandas_at_boundary:
      why:
        Pandas is used for file loading or tabular manipulation at the edge, then the code normalizes into explicit shapes.
      code: |
        from dataclasses import dataclass
        import pandas as pd

        @dataclass(frozen=True)
        class ScoreRow:
            user_id: str
            score: int

        def load_score_rows(path: str) -> list[ScoreRow]:
            frame = pd.read_csv(path)
            return [
                ScoreRow(user_id=str(row.user_id), score=int(row.score))
                for row in frame.itertuples(index=False)
            ]

    bad_pandas_everywhere:
      why:
        The DataFrame becomes the entire architecture and no stable internal model exists.
      code: |
        def do_everything(frame):
            frame = frame.merge(other_frame, on="id")
            frame["score2"] = frame["score"].fillna(0).astype(int)
            frame = frame.groupby("team").apply(custom_weird_transform)
            return frame.to_dict("records")

review_hints:
  summary:
    Use these examples directionally, not mechanically.
  rules:
    - Prefer code that looks more like the good examples and less like the bad ones.
    - If a proposed design hides data shape, control flow, or side effects, simplify it.
    - If a notebook cell contains stable logic, extract that logic into a module.
    - If a class adds no state or invariant, replace it with functions.
    - If an interface remains vague because it uses Any or dict soup, tighten the shape.

closing:
  message:
    These examples are anchors, not decoration.
    The goal is not impressive Python.
    The goal is trustworthy Python.

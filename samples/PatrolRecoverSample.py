from __future__ import annotations

from pathlib import Path
from types import ModuleType

from dreadfang.core import Df
from dreadfang.runtime import DfNodeFactory, DfRegistry
 

def _LoadNodesModule() -> ModuleType:
    module = ModuleType("PatrolRecoverNodes")
    module.Df = Df
    modulePath = Path(__file__).with_name("PatrolRecoverNodes.py")
    sourceText = modulePath.read_text(encoding="utf-8")
    exec(sourceText, module.__dict__)
    return module


PatrolRecoverNodes = _LoadNodesModule()
Root = PatrolRecoverNodes.Root
RecoverBeat = PatrolRecoverNodes.RecoverBeat


def BuildRegistry() -> DfRegistry:
    nodes: dict[str, DfNodeFactory] = {
        "RecoverBeat": RecoverBeat,
    }
    return DfRegistry(Nodes=nodes)

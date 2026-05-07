from __future__ import annotations

from dreadfang.core import Df
from dreadfang.runtime import DfNodeFactory, DfRegistry
import samples.PatrolRecoverNodes as PatrolRecoverNodes

PatrolRecoverNodes.Df = Df
Root = PatrolRecoverNodes.Root
RecoverBeat = PatrolRecoverNodes.RecoverBeat


def BuildRegistry() -> DfRegistry:
    nodes: dict[str, DfNodeFactory] = {
        "RecoverBeat": RecoverBeat,
    }
    return DfRegistry(Nodes=nodes)

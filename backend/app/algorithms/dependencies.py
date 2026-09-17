from dataclasses import dataclass

import networkx as nx


@dataclass(frozen=True)
class DependencyEdge:
    source: str
    target: str


@dataclass(frozen=True)
class DependencyAnalysis:
    missing_targets: tuple[str, ...]
    cycles: tuple[tuple[str, ...], ...]
    topological_order: tuple[str, ...]


def analyze_dependencies(item_ids: set[str], edges: list[DependencyEdge]) -> DependencyAnalysis:
    graph = nx.DiGraph()
    graph.add_nodes_from(item_ids)
    missing: set[str] = set()
    for edge in edges:
        if edge.source == edge.target:
            raise ValueError(f"Self-dependency is not allowed: {edge.source}")
        if edge.source not in item_ids:
            missing.add(edge.source)
        if edge.target not in item_ids:
            missing.add(edge.target)
        if edge.source in item_ids and edge.target in item_ids:
            graph.add_edge(edge.target, edge.source)

    cycles = tuple(tuple(cycle) for cycle in nx.simple_cycles(graph))
    order = () if cycles else tuple(nx.lexicographical_topological_sort(graph))
    return DependencyAnalysis(tuple(sorted(missing)), cycles, order)

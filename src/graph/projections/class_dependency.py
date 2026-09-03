from collections import defaultdict

from src.graph.models import EdgeType, ResolvedRelationship


class ClassDependencyProjection:
    """
    Projection exposing class-level dependencies derived from CALLS, INSTANTIATES, and COMPOSES.
    Only includes edges where both source and target normalize to a local project class.
    """

    def __init__(self):
        # fqn -> set of fqns
        self._deps_of: dict[str, set[str]] = defaultdict(set)
        self._deps_on: dict[str, set[str]] = defaultdict(set)
        
        # (source_fqn, target_fqn) -> list of relationships
        self._evidence: dict[tuple[str, str], list[ResolvedRelationship]] = defaultdict(list)
        
        self._nodes: set[str] = set()

    def add_edge(self, source_class: str, target_class: str, rel: ResolvedRelationship):
        self._nodes.add(source_class)
        self._nodes.add(target_class)
        
        self._deps_of[source_class].add(target_class)
        self._deps_on[target_class].add(source_class)
        
        self._evidence[(source_class, target_class)].append(rel)

    def nodes(self) -> set[str]:
        return self._nodes

    def dependencies_of(self, fqn: str) -> set[str]:
        return self._deps_of.get(fqn, set())

    def dependents_of(self, fqn: str) -> set[str]:
        return self._deps_on.get(fqn, set())

    def outgoing_edges(self, fqn: str) -> list[ResolvedRelationship]:
        result = []
        for target in self._deps_of.get(fqn, set()):
            result.extend(self._evidence.get((fqn, target), []))
        return result

    def incoming_edges(self, fqn: str) -> list[ResolvedRelationship]:
        result = []
        for source in self._deps_on.get(fqn, set()):
            result.extend(self._evidence.get((source, fqn), []))
        return result

    def edge_types_between(self, source: str, target: str) -> set[EdgeType]:
        rels = self._evidence.get((source, target), [])
        return {r.relationship_type for r in rels}

    def has_dependency(self, source: str, target: str) -> bool:
        return target in self._deps_of.get(source, set())

    def evidence_between(self, source: str, target: str) -> list[ResolvedRelationship]:
        return self._evidence.get((source, target), [])

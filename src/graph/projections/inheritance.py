from collections import defaultdict

from src.graph.models import ResolvedRelationship


class InheritanceProjection:
    """Projection exposing the class inheritance hierarchy derived from INHERITS relationships.

    Only includes edges where both child and parent normalize to a local project class.
    """

    def __init__(self) -> None:
        # fqn -> set of fqns
        self._parents: dict[str, set[str]] = defaultdict(set)
        self._children: dict[str, set[str]] = defaultdict(set)

        # (child_fqn, parent_fqn) -> list of relationships
        self._evidence: dict[tuple[str, str], list[ResolvedRelationship]] = defaultdict(list)

        self._nodes: set[str] = set()
        self._ancestor_cache: dict[str, set[str]] = {}
        self._descendant_cache: dict[str, set[str]] = {}

    def add_edge(self, child_class: str, parent_class: str, rel: ResolvedRelationship) -> None:
        self._nodes.add(child_class)
        self._nodes.add(parent_class)

        self._parents[child_class].add(parent_class)
        self._children[parent_class].add(child_class)

        self._evidence[(child_class, parent_class)].append(rel)
        self._ancestor_cache.clear()
        self._descendant_cache.clear()

    def nodes(self) -> set[str]:
        return self._nodes

    def parents_of(self, fqn: str) -> set[str]:
        return self._parents.get(fqn, set())

    def children_of(self, fqn: str) -> set[str]:
        return self._children.get(fqn, set())

    def ancestors_of(self, fqn: str) -> set[str]:
        if fqn in self._ancestor_cache:
            return self._ancestor_cache[fqn]
        ancestors: set[str] = set()
        queue = list(self.parents_of(fqn))
        while queue:
            curr = queue.pop(0)
            if curr not in ancestors:
                ancestors.add(curr)
                queue.extend(self.parents_of(curr))
        self._ancestor_cache[fqn] = ancestors
        return ancestors

    def descendants_of(self, fqn: str) -> set[str]:
        if fqn in self._descendant_cache:
            return self._descendant_cache[fqn]
        descendants: set[str] = set()
        queue = list(self.children_of(fqn))
        while queue:
            curr = queue.pop(0)
            if curr not in descendants:
                descendants.add(curr)
                queue.extend(self.children_of(curr))
        self._descendant_cache[fqn] = descendants
        return descendants

    def root_classes(self) -> set[str]:
        return {node for node in self._nodes if not self._parents.get(node)}

    def leaf_classes(self) -> set[str]:
        return {node for node in self._nodes if not self._children.get(node)}

    def evidence_between(self, child_class: str, parent_class: str) -> list[ResolvedRelationship]:
        return self._evidence.get((child_class, parent_class), [])

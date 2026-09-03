from collections import defaultdict

from src.graph.models import ResolvedRelationship


class ModuleCouplingProjection:
    """
    Projection exposing module-level coupling.
    Collapses resolved relationships upward to their owning modules.
    Only includes edges where both endpoints resolve to local modules.
    """

    def __init__(self):
        # module -> set of modules
        self._deps_of: dict[str, set[str]] = defaultdict(set)
        self._deps_on: dict[str, set[str]] = defaultdict(set)
        
        # (source_module, target_module) -> list of relationships
        self._evidence: dict[tuple[str, str], list[ResolvedRelationship]] = defaultdict(list)
        
        self._nodes: set[str] = set()

    def add_edge(self, source_module: str, target_module: str, rel: ResolvedRelationship):
        self._nodes.add(source_module)
        self._nodes.add(target_module)
        
        # Self-edges (intra-module coupling) are often not considered architectural coupling,
        # but for completeness we record them. However, for cycles and architectural metrics,
        # self-edges might need special handling. We keep them here.
        self._deps_of[source_module].add(target_module)
        self._deps_on[target_module].add(source_module)
        
        self._evidence[(source_module, target_module)].append(rel)

    def nodes(self) -> set[str]:
        return self._nodes

    def dependencies_of(self, module: str) -> set[str]:
        return self._deps_of.get(module, set())

    def dependents_of(self, module: str) -> set[str]:
        return self._deps_on.get(module, set())

    def fan_out(self, module: str) -> int:
        """Number of modules this module depends on (excluding itself)."""
        deps = self._deps_of.get(module, set())
        return len(deps - {module})

    def fan_in(self, module: str) -> int:
        """Number of modules depending on this module (excluding itself)."""
        deps = self._deps_on.get(module, set())
        return len(deps - {module})

    def coupling_between(self, source: str, target: str) -> int:
        """
        Weight of the coupling.
        Number of distinct deterministic relationship IDs crossing source -> target.
        """
        rels = self._evidence.get((source, target), [])
        unique_ids = {r.relationship_id for r in rels}
        return len(unique_ids)

    def outgoing_coupling(self, module: str) -> int:
        """Total weight of all outgoing dependencies (excluding self)."""
        total = 0
        for target in self._deps_of.get(module, set()):
            if target != module:
                total += self.coupling_between(module, target)
        return total

    def cycles(self) -> list[tuple[str, ...]]:
        """
        Find all elementary cycles in the module coupling graph.
        Returns canonicalized tuples to ensure determinism 
        (e.g., A -> B -> C -> A and B -> C -> A -> B both return (A, B, C) if A is the smallest).
        """
        import networkx as nx
        
        # Build a simple directed graph without self-loops for cycle detection
        G = nx.DiGraph()
        for src in self._nodes:
            G.add_node(src)
        for src, targets in self._deps_of.items():
            for tgt in targets:
                if src != tgt:
                    G.add_edge(src, tgt)
                    
        raw_cycles = list(nx.simple_cycles(G))
        
        canonical_cycles = set()
        for cycle in raw_cycles:
            # Find the minimum element to rotate the cycle to a canonical start
            min_idx = cycle.index(min(cycle))
            canonical = tuple(cycle[min_idx:] + cycle[:min_idx])
            canonical_cycles.add(canonical)
            
        return sorted(canonical_cycles)

    def evidence_between(self, source: str, target: str) -> list[ResolvedRelationship]:
        return self._evidence.get((source, target), [])

from .models import PredicateResult


class ArchitecturePredicates:
    """Predicates for detecting module and architecture level concepts based on graph metrics."""
    
    def __init__(self, metrics: dict):
        self.metrics = metrics or {}

    def _check_heuristic(self, fqn: str, signals: list, req_matched: bool, explanation_true: str, explanation_false: str) -> PredicateResult:
        return PredicateResult(
            matched=req_matched,
            confidence="MEDIUM" if req_matched else "LOW",
            signals=tuple(signals) if req_matched else (),
            explanation=explanation_true if req_matched else explanation_false
        )

    def _result(self, matched: bool, signals: list, evidence: str) -> PredicateResult:
        return PredicateResult(
            matched=matched,
            confidence="MEDIUM" if matched else "LOW",
            signals=tuple(signals) if matched else (),
            explanation=evidence if matched else ""
        )

    def is_central_module(self, fqn: str) -> PredicateResult:
        # High PageRank indicates central module
        # Assuming FQN is a file path since architecture graph is file-to-file
        metric = self.metrics.get(fqn, {})
        pr = metric.get("pagerank", 0.0)
        matched = pr > 0.01  # Arbitrary threshold, better to use relative ranking
        return self._check_heuristic(
            fqn, ["central_module"], matched,
            f"{fqn} is a central module (PageRank={pr:.4f}).",
            f"{fqn} is not a central module."
        )

    def has_centralized_hub(self) -> PredicateResult:
        if not self.metrics:
            return self._result(False, [], "")
            
        centralities = self.metrics.get("betweenness_centrality", {})
        if not centralities:
            return self._result(False, [], "")
            
        max_cent = max(centralities.values())
        matched = max_cent > 0.5
        
        return self._result(
            matched=matched,
            signals=["centralized_hub"] if matched else [],
            evidence=f"Max betweenness centrality is {max_cent:.2f}"
        )
        
    def has_generic_graph(self) -> PredicateResult:
        return self._result(True, ["graph_topology"], "Evaluated graph structure.")

    def is_dependency_hotspot(self, fqn: str) -> PredicateResult:
        metric = self.metrics.get(fqn, {})
        core = metric.get("core_number", 0)
        matched = core >= 3
        return self._check_heuristic(
            fqn, ["dependency_hotspots"], matched,
            f"{fqn} is a dependency hotspot (K-Core={core}).",
            f"{fqn} is not a dependency hotspot."
        )

    def is_boundary_violation(self, fqn: str) -> PredicateResult:
        matched = self.metrics.get(fqn, {}).get("betweenness", 0) > 0 and self.metrics.get(fqn, {}).get("pagerank", 0) < 0.005
        return self._check_heuristic(
            fqn, ["boundary_violations"], matched,
            f"{fqn} has potential boundary violations.",
            f"{fqn} does not have obvious boundary violations."
        )

    def has_abstraction_boundary(self, fqn: str) -> PredicateResult:
        return self._check_heuristic(
            fqn, ["abstraction_boundary"], False,
            f"{fqn} acts as an abstraction boundary.",
            f"{fqn} does not act as an abstraction boundary."
        )

    def is_unstable_dependency(self, fqn: str) -> PredicateResult:
        matched = self.metrics.get(fqn, {}).get("scc_size", 0) > 3
        return self._check_heuristic(
            fqn, ["unstable_dependency"], matched,
            f"{fqn} is an unstable dependency (part of SCC size > 3).",
            f"{fqn} does not seem like an unstable dependency."
        )

    def is_unstable_module(self, fqn: str) -> PredicateResult:
        return self.is_unstable_dependency(fqn)

    def is_architectural_bridge(self, fqn: str) -> PredicateResult:
        metric = self.metrics.get(fqn, {})
        bw = metric.get("betweenness", metric.get("betweenness_centrality", 0.0))
        matched = bw > 0.05
        return self._check_heuristic(
            fqn, ["architectural_bridge"], matched,
            f"{fqn} acts as an architectural bridge (Betweenness={bw:.4f}).",
            f"{fqn} is not an architectural bridge."
        )

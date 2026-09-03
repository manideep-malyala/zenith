
from src.graph.projections.module_coupling import ModuleCouplingProjection
from src.resolution.registry import GlobalSymbolRegistry

from .models import PredicateResult


class CouplingPredicates:
    """Predicates wrapping ModuleCouplingProjection."""
    
    def __init__(self, projection: ModuleCouplingProjection, registry: GlobalSymbolRegistry):
        self.projection = projection
        self.registry = registry

    def module_depends_on(self, source: str, target: str) -> PredicateResult:
        weight = self.projection.coupling_between(source, target)
        evidence = self.projection.evidence_between(source, target)
        ids = {r.relationship_id for r in evidence}
        return PredicateResult(matched=weight > 0, evidence_relationship_ids=ids)

    def fan_in(self, module: str) -> int:
        return self.projection.fan_in(module)

    def fan_out(self, module: str) -> int:
        return self.projection.fan_out(module)

    def has_high_fan_in(self, module: str) -> PredicateResult:
        fan_in_val = self.fan_in(module)
        # Using a simple heuristic threshold for "high"
        matched = fan_in_val >= 5
        
        ids = set()
        if matched:
            for dep in self.projection.dependents_of(module):
                ids.update(r.relationship_id for r in self.projection.evidence_between(dep, module))
                
        return PredicateResult(
            matched=matched,
            confidence="HIGH" if matched else "LOW",
            signals=("high_fan_in",) if matched else (),
            evidence_relationship_ids=ids,
            explanation=f"{module} has high fan-in ({fan_in_val} dependents)." if matched else f"{module} has normal/low fan-in."
        )

    def has_high_fan_out(self, module: str) -> PredicateResult:
        fan_out_val = self.fan_out(module)
        matched = fan_out_val >= 5
        
        ids = set()
        if matched:
            for dep in self.projection.dependencies_of(module):
                ids.update(r.relationship_id for r in self.projection.evidence_between(module, dep))
                
        return PredicateResult(
            matched=matched,
            confidence="HIGH" if matched else "LOW",
            signals=("high_fan_out",) if matched else (),
            evidence_relationship_ids=ids,
            explanation=f"{module} has high fan-out (depends on {fan_out_val} modules)." if matched else f"{module} has normal/low fan-out."
        )

    def is_cyclic(self, module: str) -> PredicateResult:
        # A module is cyclic if it appears in any cycle.
        all_cycles = self.projection.cycles()
        involved_cycles = [c for c in all_cycles if module in c]
        
        # We attribute evidence by aggregating all edges in the involved cycles
        ids = set()
        for cycle in involved_cycles:
            for i in range(len(cycle)):
                src = cycle[i]
                tgt = cycle[(i + 1) % len(cycle)]
                ids.update(r.relationship_id for r in self.projection.evidence_between(src, tgt))
                
        return PredicateResult(matched=bool(involved_cycles), evidence_relationship_ids=ids)

    def cycles(self) -> list[tuple[str, ...]]:
        return self.projection.cycles()

    def is_highly_coupled(self, module: str, threshold: int) -> PredicateResult:
        """
        Returns true if the total coupling (fan_in + fan_out) exceeds the given threshold.
        Evidence is all inbound and outbound edges.
        """
        total_coupling = self.fan_in(module) + self.fan_out(module)
        matched = total_coupling > threshold
        
        ids = set()
        if matched:
            for dep in self.projection.dependencies_of(module):
                ids.update(r.relationship_id for r in self.projection.evidence_between(module, dep))
            for dep in self.projection.dependents_of(module):
                ids.update(r.relationship_id for r in self.projection.evidence_between(dep, module))
                
        return PredicateResult(matched=matched, evidence_relationship_ids=ids)

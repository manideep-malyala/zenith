
from src.graph.models import EdgeType
from src.graph.projections.class_dependency import ClassDependencyProjection
from src.resolution.registry import GlobalSymbolRegistry

from .models import PredicateResult


class CompositionPredicates:
    """Predicates wrapping compositional evidence within ClassDependencyProjection."""
    
    def __init__(self, projection: ClassDependencyProjection, registry: GlobalSymbolRegistry):
        self.projection = projection
        self.registry = registry

    def _evidence_ids(self, owner: str, dependency: str) -> set:
        evidence = self.projection.evidence_between(owner, dependency)
        return {r.relationship_id for r in evidence if r.relationship_type == EdgeType.COMPOSES}

    def is_composed_of(self, owner: str, dependency: str) -> PredicateResult:
        ids = self._evidence_ids(owner, dependency)
        return PredicateResult(matched=bool(ids), evidence_relationship_ids=ids)

    def composed_dependencies(self, class_fqn: str) -> set[str]:
        composed = set()
        for dep in self.projection.dependencies_of(class_fqn):
            if EdgeType.COMPOSES in self.projection.edge_types_between(class_fqn, dep):
                composed.add(dep)
        return composed

    def has_aggregation(self, class_fqn: str) -> PredicateResult:
        composed = self.composed_dependencies(class_fqn)
        matched = bool(composed)
        
        ids = set()
        for dep in composed:
            ids.update(self._evidence_ids(class_fqn, dep))
            
        return PredicateResult(
            matched=matched,
            confidence="HIGH" if matched else "LOW",
            signals=("aggregation",) if matched else (),
            evidence_relationship_ids=ids,
            explanation=f"{class_fqn} aggregates other classes: {sorted(composed)}." if matched else f"{class_fqn} does not aggregate other classes."
        )
        
    def has_dependency_relationships(self, class_fqn: str) -> PredicateResult:
        deps = self.projection.dependencies_of(class_fqn)
        matched = bool(deps)
        return PredicateResult(
            matched=matched,
            confidence="HIGH" if matched else "LOW",
            signals=("dependencies",) if matched else (),
            explanation=f"{class_fqn} has {len(deps)} class dependencies." if matched else f"{class_fqn} has no class dependencies."
        )

    def has_encapsulation(self, class_fqn: str) -> PredicateResult:
        # Heuristic: does the class define private/protected attributes (_xxx)?
        prefix = class_fqn + "."
        has_privates = False
        for fqn, defn in self.registry.definitions_by_fqn.items():
            if fqn.startswith(prefix) and fqn.count(".") == prefix.count("."):
                if defn.name.startswith("_") and not defn.name.startswith("__"):
                    has_privates = True
                    break
        
        return PredicateResult(
            matched=has_privates,
            confidence="MEDIUM" if has_privates else "LOW",
            signals=("encapsulation",) if has_privates else (),
            explanation=f"{class_fqn} defines protected/private members." if has_privates else f"{class_fqn} does not explicitly encapsulate members via naming conventions."
        )

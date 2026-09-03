from src.graph.models import EdgeType
from src.graph.projections.inheritance import InheritanceProjection
from src.resolution.registry import GlobalSymbolRegistry

from .models import PredicateResult


class InheritancePredicates:
    """Predicates wrapping InheritanceProjection."""

    def __init__(self, projection: InheritanceProjection, registry: GlobalSymbolRegistry):
        self.projection = projection
        self.registry = registry

    def _evidence_ids(self, child: str, parent: str) -> set:
        evidence = self.projection.evidence_between(child, parent)
        return {r.relationship_id for r in evidence if r.relationship_type == EdgeType.INHERITS}

    def inherits_from(self, child: str, parent: str) -> PredicateResult:
        ids = self._evidence_ids(child, parent)
        return PredicateResult(
            matched=bool(ids),
            confidence="HIGH" if ids else "LOW",
            signals=("inherits_from",) if ids else (),
            evidence_edge_ids=ids,
            explanation="Inheritance edge exists between child and parent." if ids else "No inheritance edge found.",
            evidence_relationship_ids=ids,
        )

    def has_children(self, class_fqn: str) -> PredicateResult:
        children = self.projection.children_of(class_fqn)
        ids = set()
        for child in children:
            ids.update(self._evidence_ids(child, class_fqn))
        return PredicateResult(
            matched=bool(ids),
            confidence="HIGH" if ids else "LOW",
            signals=("has_children",) if ids else (),
            evidence_edge_ids=ids,
            explanation=f"{class_fqn} has {len(children)} direct subclass(es)." if ids else f"{class_fqn} has no direct subclasses.",
            evidence_relationship_ids=ids,
        )

    def has_subclasses(self, class_fqn: str) -> PredicateResult:
        return self.has_children(class_fqn)

    def has_method_overrides(self, class_fqn: str) -> PredicateResult:
        ancestors = self.projection.ancestors_of(class_fqn)
        if not ancestors:
            return PredicateResult(
                matched=False,
                confidence="LOW",
                signals=("method_overrides",),
                explanation=f"{class_fqn} has no local ancestors.",
            )

        # Local methods of class_fqn
        class_methods = set()
        prefix = class_fqn + "."
        for fqn, defn in self.registry.definitions_by_fqn.items():
            if defn.definition_type == "method" and fqn.startswith(prefix) and fqn.count(".") == prefix.count("."):
                class_methods.add(defn.name)

        if not class_methods:
            return PredicateResult(
                matched=False,
                confidence="HIGH",
                signals=("method_overrides",),
                explanation=f"{class_fqn} defines no local methods.",
            )

        # Check if any class method exists in ancestors
        overridden = []
        for ancestor in ancestors:
            anc_prefix = ancestor + "."
            for fqn, defn in self.registry.definitions_by_fqn.items():
                if defn.definition_type == "method" and fqn.startswith(anc_prefix) and fqn.count(".") == anc_prefix.count("."):
                    if defn.name in class_methods:
                        overridden.append((defn.name, ancestor))

        matched = bool(overridden)
        
        evidence_ids = set()
        if matched:
            for _, ancestor in overridden:
                evidence_ids.update(self._evidence_ids(class_fqn, ancestor))
                
        return PredicateResult(
            matched=matched,
            confidence="HIGH" if matched else "MEDIUM",
            signals=("method_overrides",) if matched else (),
            evidence_edge_ids=evidence_ids,
            evidence_relationship_ids=evidence_ids,
            explanation=f"{class_fqn} overrides methods: {[m[0] for m in overridden]}" if matched else f"{class_fqn} does not override ancestor methods.",
        )

    def has_multiple_children(self, class_fqn: str) -> PredicateResult:
        children = self.projection.children_of(class_fqn)
        if len(children) < 2:
            return PredicateResult(
                matched=False,
                confidence="LOW",
                signals=("multiple_children",),
                explanation=f"{class_fqn} does not have multiple direct subclasses.",
            )
        ids = set()
        for child in children:
            ids.update(self._evidence_ids(child, class_fqn))
        return PredicateResult(
            matched=True,
            confidence="HIGH",
            signals=("multiple_children", "polymorphic_family"),
            evidence_edge_ids=ids,
            explanation=f"{class_fqn} has multiple direct subclasses, indicating a polymorphic family.",
            evidence_relationship_ids=ids,
        )

    def is_root_class(self, class_fqn: str) -> PredicateResult:
        parents = self.projection.parents_of(class_fqn)
        return PredicateResult(
            matched=len(parents) == 0,
            confidence="MEDIUM",
            signals=("root_class",),
            explanation=f"{class_fqn} has no local parent classes." if len(parents) == 0 else f"{class_fqn} has local parent classes.",
        )

    def is_leaf_class(self, class_fqn: str) -> PredicateResult:
        children = self.projection.children_of(class_fqn)
        return PredicateResult(
            matched=len(children) == 0,
            confidence="MEDIUM",
            signals=("leaf_class",),
            explanation=f"{class_fqn} has no subclasses." if len(children) == 0 else f"{class_fqn} has subclasses.",
        )

    def shares_parent(self, a: str, b: str) -> PredicateResult:
        parents_a = self.projection.parents_of(a)
        parents_b = self.projection.parents_of(b)
        common = parents_a.intersection(parents_b)

        ids = set()
        for p in common:
            ids.update(self._evidence_ids(a, p))
            ids.update(self._evidence_ids(b, p))

        return PredicateResult(
            matched=bool(common),
            confidence="HIGH" if common else "LOW",
            signals=("shared_parent",) if common else (),
            evidence_edge_ids=ids,
            explanation=f"{a} and {b} share parent(s): {sorted(common)}." if common else f"{a} and {b} do not share a parent.",
            evidence_relationship_ids=ids,
        )

    def is_polymorphic_family(self, base_fqn: str) -> PredicateResult:
        return self.has_multiple_children(base_fqn)

    def hierarchy_depth(self, class_fqn: str) -> int:
        parents = self.projection.parents_of(class_fqn)
        if not parents:
            return 0
        return 1 + max(self.hierarchy_depth(p) for p in parents)
        
    def has_multiple_inheritance(self, class_fqn: str) -> PredicateResult:
        parents = self.projection.parents_of(class_fqn)
        matched = len(parents) > 1
        ids = set()
        if matched:
            for parent in parents:
                ids.update(self._evidence_ids(class_fqn, parent))
        return PredicateResult(
            matched=matched,
            confidence="HIGH" if matched else "LOW",
            signals=("multiple_inheritance",) if matched else (),
            evidence_relationship_ids=ids,
            explanation=f"{class_fqn} inherits from multiple parents." if matched else f"{class_fqn} does not use multiple inheritance."
        )

    def is_abstract_class(self, class_fqn: str) -> PredicateResult:
        parents = self.projection.parents_of(class_fqn)
        is_abc = "abc.ABC" in parents or any("ABC" in p for p in parents)
        # Note: We can also check if it contains abstractmethod decorators using AST features, 
        # but parent check is simplest for now.
        
        ids = set()
        if is_abc:
            for parent in parents:
                if "ABC" in parent:
                    ids.update(self._evidence_ids(class_fqn, parent))
                    
        return PredicateResult(
            matched=is_abc,
            confidence="MEDIUM" if is_abc else "LOW",
            signals=("abstract_class",) if is_abc else (),
            evidence_relationship_ids=ids,
            explanation=f"{class_fqn} is an abstract base class." if is_abc else f"{class_fqn} is not an abstract class."
        )

    def is_protocol(self, class_fqn: str) -> PredicateResult:
        parents = self.projection.parents_of(class_fqn)
        is_proto = "typing.Protocol" in parents or any("Protocol" in p for p in parents)
        
        ids = set()
        if is_proto:
            for parent in parents:
                if "Protocol" in parent:
                    ids.update(self._evidence_ids(class_fqn, parent))
                    
        return PredicateResult(
            matched=is_proto,
            confidence="HIGH" if is_proto else "LOW",
            signals=("protocol_interface",) if is_proto else (),
            evidence_relationship_ids=ids,
            explanation=f"{class_fqn} is a typing.Protocol interface." if is_proto else f"{class_fqn} is not a protocol."
        )

    def has_mixins(self, class_fqn: str) -> PredicateResult:
        parents = self.projection.parents_of(class_fqn)
        mixin_parents = [p for p in parents if "Mixin" in p.split(".")[-1]]
        matched = bool(mixin_parents)
        
        ids = set()
        if matched:
            for p in mixin_parents:
                ids.update(self._evidence_ids(class_fqn, p))
                
        return PredicateResult(
            matched=matched,
            confidence="HIGH" if matched else "LOW",
            signals=("uses_mixins",) if matched else (),
            evidence_relationship_ids=ids,
            explanation=f"{class_fqn} uses mixins: {mixin_parents}." if matched else f"{class_fqn} does not use mixins."
        )

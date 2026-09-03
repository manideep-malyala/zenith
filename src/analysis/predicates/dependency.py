
from src.graph.models import EdgeType
from src.graph.projections.class_dependency import ClassDependencyProjection
from src.resolution.registry import GlobalSymbolRegistry

from .models import PredicateResult


class DependencyPredicates:
    """Predicates wrapping ClassDependencyProjection."""

    def __init__(self, projection: ClassDependencyProjection, registry: GlobalSymbolRegistry):
        self.projection = projection
        self.registry = registry

    def _evidence_ids(self, source: str, target: str, edge_types: set[EdgeType] | None = None) -> set:
        evidence = self.projection.evidence_between(source, target)
        if edge_types is not None:
            return {r.relationship_id for r in evidence if r.relationship_type in edge_types}
        return {r.relationship_id for r in evidence}

    def depends_on(self, source: str, target: str) -> PredicateResult:
        """Returns true if source has any dependency on target."""
        ids = self._evidence_ids(source, target)
        return PredicateResult(
            matched=bool(ids),
            confidence="HIGH" if ids else "LOW",
            signals=("depends_on",) if ids else (),
            evidence_edge_ids=ids,
            explanation=f"{source} depends on {target}." if ids else f"{source} does not depend on {target}.",
            evidence_relationship_ids=ids,
        )
        
    def depends_on_package(self, source: str, package_name: str) -> PredicateResult:
        """Returns true if source depends on any module within package_name."""
        ids = set()
        for dep in self.projection.dependencies_of(source):
            if dep == package_name or dep.startswith(package_name + "."):
                ids.update(self._evidence_ids(source, dep))
                
        matched = bool(ids)
        return PredicateResult(
            matched=matched,
            confidence="HIGH" if matched else "LOW",
            signals=(f"uses_{package_name.replace('.', '_')}",) if matched else (),
            evidence_relationship_ids=ids,
            explanation=f"{source} depends on package {package_name}." if matched else f"{source} does not depend on {package_name}."
        )

    def calls(self, source: str, target: str) -> PredicateResult:
        ids = self._evidence_ids(source, target, {EdgeType.CALLS})
        return PredicateResult(
            matched=bool(ids),
            confidence="HIGH" if ids else "LOW",
            signals=("calls",),
            evidence_edge_ids=ids,
            explanation=f"{source} calls {target}." if ids else f"{source} does not call {target}.",
            evidence_relationship_ids=ids,
        )

    def instantiates(self, source: str, target: str) -> PredicateResult:
        ids = self._evidence_ids(source, target, {EdgeType.INSTANTIATES})
        return PredicateResult(
            matched=bool(ids),
            confidence="HIGH" if ids else "LOW",
            signals=("instantiates",),
            evidence_edge_ids=ids,
            explanation=f"{source} instantiates {target}." if ids else f"{source} does not instantiate {target}.",
            evidence_relationship_ids=ids,
        )

    def composes(self, source: str, target: str) -> PredicateResult:
        ids = self._evidence_ids(source, target, {EdgeType.COMPOSES})
        return PredicateResult(
            matched=bool(ids),
            confidence="HIGH" if ids else "LOW",
            signals=("composes",),
            evidence_edge_ids=ids,
            explanation=f"{source} composes {target}." if ids else f"{source} does not compose {target}.",
            evidence_relationship_ids=ids,
        )

    def has_bidirectional_dependency(self, a: str, b: str) -> PredicateResult:
        a_to_b = self._evidence_ids(a, b)
        b_to_a = self._evidence_ids(b, a)
        matched = bool(a_to_b and b_to_a)
        evidence = a_to_b | b_to_a if matched else set()
        return PredicateResult(
            matched=matched,
            confidence="HIGH" if matched else "LOW",
            signals=("bidirectional_dependency",) if matched else (),
            evidence_edge_ids=evidence,
            explanation=f"{a} and {b} are mutually dependent." if matched else f"{a} and {b} are not mutually dependent.",
            evidence_relationship_ids=evidence,
        )

    def delegates_to_collaborator(self, source: str, target: str) -> PredicateResult:
        calls = self._evidence_ids(source, target, {EdgeType.CALLS})
        composes = self._evidence_ids(source, target, {EdgeType.COMPOSES})
        matched = bool(calls and composes)
        ids = calls | composes if matched else set()
        return PredicateResult(
            matched=matched,
            confidence="HIGH" if matched else "LOW",
            signals=("delegates_to_collaborator",) if matched else (),
            evidence_edge_ids=ids,
            explanation=f"{source} delegates work to {target}." if matched else f"{source} does not delegate to {target}.",
            evidence_relationship_ids=ids,
        )

    def depends_on_abstraction(self, source: str, target: str) -> PredicateResult:
        ids = self._evidence_ids(source, target, {EdgeType.COMPOSES, EdgeType.CALLS})
        matched = bool(ids)
        return PredicateResult(
            matched=matched,
            confidence="MEDIUM" if matched else "LOW",
            signals=("depends_on_abstraction",) if matched else (),
            evidence_edge_ids=ids,
            explanation=f"{source} depends on an abstraction represented by {target}." if matched else f"{source} does not show a clear abstraction dependency on {target}.",
            evidence_relationship_ids=ids,
        )

    def has_constructor_injection(self, class_fqn: str) -> PredicateResult:
        init_fqn = f"{class_fqn}.__init__"
        init_defn = self.registry.lookup(init_fqn)
        if not init_defn:
            return PredicateResult(
                matched=False,
                confidence="HIGH",
                signals=("constructor_injection",),
                explanation=f"{class_fqn} has no __init__ method.",
            )
            
        import ast
        try:
            with open(init_defn.file_path, encoding="utf-8") as f:
                source = f.read()
            module = ast.parse(source)
            init_node = None
            for node in ast.walk(module):
                if isinstance(node, ast.FunctionDef) and node.name == "__init__" and getattr(node, "lineno", -1) == init_defn.start_line:
                    init_node = node
                    break
                    
            if not init_node:
                return PredicateResult(
                    matched=False,
                    confidence="LOW",
                    explanation="Could not parse __init__ method.",
                )
                
            has_typed_param = False
            has_untyped_param = False
            for arg in init_node.args.args:
                if arg.arg == "self":
                    continue
                if arg.annotation:
                    has_typed_param = True
                else:
                    has_untyped_param = True
            
            if not has_typed_param and not has_untyped_param:
                return PredicateResult(
                    matched=False,
                    confidence="HIGH",
                    signals=("constructor_injection",),
                    explanation=f"{class_fqn}.__init__ takes no parameters.",
                )
                
            class_deps = self.projection.outgoing_edges(class_fqn)
            composes_edges = [e for e in class_deps if e.relationship_type == EdgeType.COMPOSES]
            
            signals = ["constructor_injection"]
            if has_typed_param:
                signals.append("typed_parameter")
            if has_untyped_param:
                signals.append("untyped_parameter")

            if composes_edges:
                edge_ids = {e.relationship_id for e in composes_edges}
                return PredicateResult(
                    matched=True,
                    confidence="HIGH" if has_typed_param else "MEDIUM",
                    signals=signals + ["composition"],
                    evidence_edge_ids=edge_ids,
                    evidence_relationship_ids=edge_ids,
                    explanation=f"{class_fqn} uses constructor injection.",
                )
            elif has_untyped_param:
                # Untyped parameter without explicit composition edges
                return PredicateResult(
                    matched=True,
                    confidence="LOW",
                    signals=signals,
                    explanation=f"{class_fqn} takes untyped parameters in constructor.",
                )
                
        except Exception:
            pass
            
        return PredicateResult(
            matched=False,
            confidence="MEDIUM",
            explanation=f"{class_fqn} does not use constructor injection.",
        )

    def dependencies_of(self, source: str) -> set[str]:
        return self.projection.dependencies_of(source)

    def dependents_of(self, target: str) -> set[str]:
        return self.projection.dependents_of(target)

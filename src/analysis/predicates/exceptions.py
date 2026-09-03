from src.core.models import RaiseFact, TryFact
from src.graph.projections.ast_features import ASTFeatureIndex
from src.graph.projections.inheritance import InheritanceProjection

from .models import PredicateResult


class ExceptionPredicates:
    def __init__(self, ast_features: ASTFeatureIndex, inheritance: InheritanceProjection):
        self.ast_features = ast_features
        self.inheritance = inheritance

    def uses_try(self, fqn: str) -> PredicateResult:
        try_facts = self.ast_features.get_facts(fqn, TryFact)
        matched = bool(try_facts)
        return PredicateResult(
            matched=matched,
            confidence="HIGH" if matched else "LOW",
            signals=("try_block",) if matched else (),
            evidence_fact_ids={f.fact_id for f in try_facts},
            explanation=f"{fqn} uses try blocks." if matched else f"{fqn} does not use try blocks."
        )

    def uses_except(self, fqn: str) -> PredicateResult:
        try_facts = self.ast_features.get_facts(fqn, TryFact)
        except_facts = [f for f in try_facts if f.handlers > 0]
        matched = bool(except_facts)
        return PredicateResult(
            matched=matched,
            confidence="HIGH" if matched else "LOW",
            signals=("except_block",) if matched else (),
            evidence_fact_ids={f.fact_id for f in except_facts},
            explanation=f"{fqn} catches exceptions." if matched else f"{fqn} does not catch exceptions."
        )

    def uses_broad_except(self, fqn: str) -> PredicateResult:
        try_facts = self.ast_features.get_facts(fqn, TryFact)
        broad_facts = []
        for fact in try_facts:
            if "BaseException" in fact.caught_exceptions or "Exception" in fact.caught_exceptions or not fact.caught_exceptions:
                broad_facts.append(fact)
                
        matched = bool(broad_facts)
        return PredicateResult(
            matched=matched,
            confidence="HIGH" if matched else "LOW",
            signals=("broad_except",) if matched else (),
            evidence_fact_ids={f.fact_id for f in broad_facts},
            explanation=f"{fqn} uses broad exception handling." if matched else f"{fqn} does not use broad exception handling."
        )
        
    def has_custom_exceptions(self, fqn: str) -> PredicateResult:
        """
        Check if the FQN (assuming it's a class) inherits from Exception/BaseException.
        We check if 'builtins.Exception' is in its parent hierarchy.
        """
        parents = self.inheritance.parents_of(fqn)
        is_exception = "builtins.Exception" in parents or "builtins.BaseException" in parents
        
        # If we just look at the base name for unresolved ones:
        if not is_exception:
            for p in parents:
                if p.endswith(("Exception", "Error")):
                    is_exception = True
                    break

        return PredicateResult(
            matched=is_exception,
            confidence="HIGH" if is_exception else "LOW",
            signals=("custom_exception",) if is_exception else (),
            evidence_edge_ids={r.relationship_id for r in self.inheritance.evidence_between(fqn, "builtins.Exception")} if is_exception else set(),
            explanation=f"{fqn} is a custom exception class." if is_exception else f"{fqn} is not a custom exception."
        )

    def uses_exception_chaining(self, fqn: str) -> PredicateResult:
        raise_facts = self.ast_features.get_facts(fqn, RaiseFact)
        chained_facts = [f for f in raise_facts if f.cause]
        matched = bool(chained_facts)
        return PredicateResult(
            matched=matched,
            confidence="HIGH" if matched else "LOW",
            signals=("exception_chaining",) if matched else (),
            evidence_fact_ids={f.fact_id for f in chained_facts},
            explanation=f"{fqn} uses exception chaining." if matched else f"{fqn} does not use exception chaining."
        )

    def has_finally_cleanup(self, fqn: str) -> PredicateResult:
        try_facts = self.ast_features.get_facts(fqn, TryFact)
        finally_facts = [f for f in try_facts if f.has_finally]
        matched = bool(finally_facts)
        return PredicateResult(
            matched=matched,
            confidence="HIGH" if matched else "LOW",
            signals=("finally_cleanup",) if matched else (),
            evidence_fact_ids={f.fact_id for f in finally_facts},
            explanation=f"{fqn} uses a finally block for cleanup." if matched else f"{fqn} does not use a finally block."
        )

    def has_exception_else(self, fqn: str) -> PredicateResult:
        try_facts = self.ast_features.get_facts(fqn, TryFact)
        else_facts = [f for f in try_facts if f.has_else]
        matched = bool(else_facts)
        return PredicateResult(
            matched=matched,
            confidence="HIGH" if matched else "LOW",
            signals=("exception_else",) if matched else (),
            evidence_fact_ids={f.fact_id for f in else_facts},
            explanation=f"{fqn} uses an else block in a try-except." if matched else f"{fqn} does not use an else block."
        )
        
    def raises_from_function(self, fqn: str) -> PredicateResult:
        raise_facts = self.ast_features.get_facts(fqn, RaiseFact)
        matched = bool(raise_facts)
        return PredicateResult(
            matched=matched,
            confidence="HIGH" if matched else "LOW",
            signals=("raises_exception",) if matched else (),
            evidence_fact_ids={f.fact_id for f in raise_facts},
            explanation=f"{fqn} explicitly raises exceptions." if matched else f"{fqn} does not raise exceptions."
        )

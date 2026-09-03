from src.core.models import (
    ComprehensionFact,
    DecoratorFact,
    GeneratorFact,
    LambdaFact,
    WithFact,
)
from src.graph.projections.ast_features import ASTFeatureIndex

from .models import PredicateResult


class IdiomPredicates:
    def __init__(self, ast_features: ASTFeatureIndex):
        self.ast_features = ast_features

    def _check_heuristic(self, fqn: str, signals: list, req_matched: bool, explanation_true: str, explanation_false: str) -> PredicateResult:
        return PredicateResult(
            matched=req_matched,
            confidence="MEDIUM" if req_matched else "LOW",
            signals=tuple(signals) if req_matched else (),
            explanation=explanation_true if req_matched else explanation_false
        )

    def has_complex_list_comprehension(self, fqn: str) -> PredicateResult:
        # A list comp with multiple generators or ifs is complex
        res = self.uses_comprehensions(fqn)
        return self._check_heuristic(
            fqn, ["complex_list_comprehension"], res.matched,
            f"{fqn} contains complex list comprehensions.",
            f"{fqn} does not have obvious complex list comprehensions."
        )

    def has_generic_idiom(self, fqn: str) -> PredicateResult:
        return self._check_heuristic(
            fqn, ["pythonic_idiom"], True,
            f"{fqn} evaluated for pythonic idioms.",
            ""
        )

    def uses_comprehensions(self, fqn: str) -> PredicateResult:
        comp_facts = self.ast_features.get_facts(fqn, ComprehensionFact)
        matched = bool(comp_facts)
        return PredicateResult(
            matched=matched,
            confidence="HIGH" if matched else "LOW",
            signals=("comprehension",) if matched else (),
            evidence_fact_ids={f.fact_id for f in comp_facts},
            explanation=f"{fqn} uses comprehensions (list, dict, set, or generator)." if matched else f"{fqn} does not use comprehensions."
        )

    def is_generator(self, fqn: str) -> PredicateResult:
        gen_facts = self.ast_features.get_facts(fqn, GeneratorFact)
        matched = bool(gen_facts)
        return PredicateResult(
            matched=matched,
            confidence="HIGH" if matched else "LOW",
            signals=("generator",) if matched else (),
            evidence_fact_ids={f.fact_id for f in gen_facts},
            explanation=f"{fqn} is a generator function (uses yield)." if matched else f"{fqn} does not yield."
        )

    def uses_yield(self, fqn: str) -> PredicateResult:
        gen_facts = self.ast_features.get_facts(fqn, GeneratorFact)
        yield_facts = [f for f in gen_facts if f.kind == 'yield']
        matched = bool(yield_facts)
        return PredicateResult(
            matched=matched,
            confidence="HIGH" if matched else "LOW",
            signals=("yield",) if matched else (),
            evidence_fact_ids={f.fact_id for f in yield_facts},
            explanation=f"{fqn} yields values." if matched else f"{fqn} does not yield values."
        )

    def uses_yield_from(self, fqn: str) -> PredicateResult:
        gen_facts = self.ast_features.get_facts(fqn, GeneratorFact)
        yield_from_facts = [f for f in gen_facts if f.kind == 'yield_from']
        matched = bool(yield_from_facts)
        return PredicateResult(
            matched=matched,
            confidence="HIGH" if matched else "LOW",
            signals=("yield_from",) if matched else (),
            evidence_fact_ids={f.fact_id for f in yield_from_facts},
            explanation=f"{fqn} yields from another iterable." if matched else f"{fqn} does not yield from."
        )

    def uses_generator_expression(self, fqn: str) -> PredicateResult:
        comp_facts = self.ast_features.get_facts(fqn, ComprehensionFact)
        gen_expr_facts = [f for f in comp_facts if f.kind == 'generator']
        matched = bool(gen_expr_facts)
        return PredicateResult(
            matched=matched,
            confidence="HIGH" if matched else "LOW",
            signals=("generator_expression",) if matched else (),
            evidence_fact_ids={f.fact_id for f in gen_expr_facts},
            explanation=f"{fqn} uses generator expressions." if matched else f"{fqn} does not use generator expressions."
        )

    def uses_context_managers(self, fqn: str) -> PredicateResult:
        with_facts = self.ast_features.get_facts(fqn, WithFact)
        matched = bool(with_facts)
        return PredicateResult(
            matched=matched,
            confidence="HIGH" if matched else "LOW",
            signals=("context_manager",) if matched else (),
            evidence_fact_ids={f.fact_id for f in with_facts},
            explanation=f"{fqn} uses context managers ('with' block)." if matched else f"{fqn} does not use context managers."
        )

    def uses_lambdas(self, fqn: str) -> PredicateResult:
        lambda_facts = self.ast_features.get_facts(fqn, LambdaFact)
        matched = bool(lambda_facts)
        return PredicateResult(
            matched=matched,
            confidence="HIGH" if matched else "LOW",
            signals=("lambda",) if matched else (),
            evidence_fact_ids={f.fact_id for f in lambda_facts},
            explanation=f"{fqn} uses lambda expressions." if matched else f"{fqn} does not use lambdas."
        )

    def uses_decorators(self, fqn: str) -> PredicateResult:
        decorator_facts = self.ast_features.get_facts(fqn, DecoratorFact)
        matched = bool(decorator_facts)
        return PredicateResult(
            matched=matched,
            confidence="HIGH" if matched else "LOW",
            signals=("decorator",) if matched else (),
            evidence_fact_ids={f.fact_id for f in decorator_facts},
            explanation=f"{fqn} uses decorators." if matched else f"{fqn} does not use decorators."
        )

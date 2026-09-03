import unittest

from src.analysis.predicates.concurrency import ConcurrencyPredicates
from src.analysis.predicates.dependency import DependencyPredicates
from src.analysis.predicates.exceptions import ExceptionPredicates
from src.analysis.predicates.idioms import IdiomPredicates
from src.core.context import ASTContext
from src.core.models import GeneratorFact, LambdaFact, RaiseFact, TryFact
from src.graph.models import EdgeType, ResolvedRelationship
from src.graph.projections.ast_features import ASTFeatureIndex
from src.graph.projections.class_dependency import ClassDependencyProjection
from src.graph.projections.inheritance import InheritanceProjection
from src.resolution.registry import GlobalSymbolRegistry


class TestCoverageMatrix(unittest.TestCase):
    """
    A question-to-predicate coverage test to ensure our predicates can answer 
    real engineering questions from the user.
    """
    def setUp(self):
        self.registry = GlobalSymbolRegistry("/repo")
        self.registry._file_to_module = lambda fp: "app"
        
        self.ast_features = ASTFeatureIndex()
        self.class_deps = ClassDependencyProjection()
        self.inheritance = InheritanceProjection()
        
        self.dependency = DependencyPredicates(self.class_deps, self.registry)
        self.idioms = IdiomPredicates(self.ast_features)
        self.exceptions = ExceptionPredicates(self.ast_features, self.inheritance)
        self.concurrency = ConcurrencyPredicates(self.ast_features, self.dependency)
        
    def test_question_where_are_lambdas_used(self):
        # Q: Where are lambdas used?
        # Requires: IdiomPredicates.uses_lambdas() -> matched = True
        ctx = ASTContext(enclosing_function="process")
        fact = LambdaFact("/repo/app.py", 1, [], 0, context=ctx)
        self.ast_features.build([fact], self.registry)
        
        res = self.idioms.uses_lambdas("app.process")
        self.assertTrue(res.matched)

    def test_question_where_are_generators_used(self):
        # Q: Where are generators used?
        # Requires: IdiomPredicates.is_generator() -> matched = True
        ctx = ASTContext(enclosing_function="process")
        fact = GeneratorFact("/repo/app.py", 1, "yield", context=ctx)
        self.ast_features.build([fact], self.registry)
        
        res = self.idioms.is_generator("app.process")
        self.assertTrue(res.matched)

    def test_question_where_are_broad_exceptions_used(self):
        # Q: Where are broad exceptions used?
        # Requires: ExceptionPredicates.uses_broad_except() -> matched = True
        ctx = ASTContext(enclosing_function="process")
        fact = TryFact("/repo/app.py", 1, 1, False, False, ["Exception"], context=ctx)
        self.ast_features.build([fact], self.registry)
        
        res = self.exceptions.uses_broad_except("app.process")
        self.assertTrue(res.matched)

    def test_question_where_is_exception_chaining_used(self):
        # Q: Where is exception chaining used?
        # Requires: ExceptionPredicates.uses_exception_chaining() -> matched = True
        ctx = ASTContext(enclosing_function="process")
        fact = RaiseFact("/repo/app.py", 1, "ValueError()", "e", context=ctx)
        self.ast_features.build([fact], self.registry)
        
        res = self.exceptions.uses_exception_chaining("app.process")
        self.assertTrue(res.matched)

    def test_question_where_are_locks_used(self):
        # Q: Where are locks used?
        # Requires: ConcurrencyPredicates.uses_locks() -> matched = True
        rel = ResolvedRelationship(
            relationship_type=EdgeType.CALLS, source_fqn="app.process",
            target_fqn="threading.Lock", resolution_status="RESOLVED",
            resolution_domain="EXTERNAL", confidence="HIGH",
            resolution_method="EXPLICIT_IMPORT", evidence_fact_ids=[]
        )
        self.class_deps.add_edge("app.process", "threading.Lock", rel)
        
        res = self.concurrency.uses_locks("app.process")
        self.assertTrue(res.matched)

    def test_question_where_are_thread_pools_used(self):
        # Q: Where are thread pools used?
        # Requires: ConcurrencyPredicates.uses_thread_pool() -> matched = True
        rel = ResolvedRelationship(
            relationship_type=EdgeType.CALLS, source_fqn="app.process",
            target_fqn="concurrent.futures.ThreadPoolExecutor", resolution_status="RESOLVED",
            resolution_domain="EXTERNAL", confidence="HIGH",
            resolution_method="EXPLICIT_IMPORT", evidence_fact_ids=[]
        )
        self.class_deps.add_edge("app.process", "concurrent.futures.ThreadPoolExecutor", rel)
        
        res = self.concurrency.uses_thread_pool("app.process")
        self.assertTrue(res.matched)

if __name__ == "__main__":
    unittest.main()

import unittest

from src.analysis.predicates.exceptions import ExceptionPredicates
from src.core.context import ASTContext
from src.core.models import RaiseFact, TryFact
from src.graph.models import EdgeType, ResolvedRelationship
from src.graph.projections.ast_features import ASTFeatureIndex
from src.graph.projections.inheritance import InheritanceProjection
from src.resolution.registry import GlobalSymbolRegistry


class TestExceptionPredicates(unittest.TestCase):
    def setUp(self):
        self.registry = GlobalSymbolRegistry("/repo")
        self.registry._file_to_module = lambda fp: "app"
        
        self.ast_features = ASTFeatureIndex()
        self.inheritance = InheritanceProjection()
        
    def _run_exception(self, facts, predicate_method, fqn="app.Service.process"):
        self.ast_features.build(facts, self.registry)
        predicates = ExceptionPredicates(self.ast_features, self.inheritance)
        return getattr(predicates, predicate_method)(fqn)
        
    def test_uses_broad_except(self):
        ctx = ASTContext(enclosing_class="Service", enclosing_function="process")
        fact = TryFact(
            file_path="/repo/app.py", line=1, handlers=1, has_else=False, has_finally=False,
            caught_exceptions=["BaseException"], context=ctx
        )
        res = self._run_exception([fact], "uses_broad_except")
        self.assertTrue(res.matched)
        self.assertIn("broad_except", res.signals)

    def test_uses_broad_except_negative(self):
        ctx = ASTContext(enclosing_class="Service", enclosing_function="process")
        fact = TryFact(
            file_path="/repo/app.py", line=1, handlers=1, has_else=False, has_finally=False,
            caught_exceptions=["ValueError"], context=ctx
        )
        res = self._run_exception([fact], "uses_broad_except")
        self.assertFalse(res.matched)

    def test_has_custom_exceptions(self):
        # fqn = "app.MyError"
        rel = ResolvedRelationship(
            relationship_type=EdgeType.INHERITS,
            source_fqn="app.MyError",
            target_fqn="builtins.Exception",
            resolution_status="RESOLVED",
            resolution_domain="BUILTIN",
            confidence="HIGH",
            resolution_method="BUILTIN",
            evidence_fact_ids=[]
        )
        self.inheritance.add_edge("app.MyError", "builtins.Exception", rel)
        
        predicates = ExceptionPredicates(self.ast_features, self.inheritance)
        res = predicates.has_custom_exceptions("app.MyError")
        self.assertTrue(res.matched)
        self.assertIn("custom_exception", res.signals)

    def test_uses_exception_chaining(self):
        ctx = ASTContext(enclosing_function="process")
        fact = RaiseFact(
            file_path="/repo/app.py", line=1, exception_expression="ValueError()",
            cause="e", context=ctx
        )
        res = self._run_exception([fact], "uses_exception_chaining", fqn="app.process")
        self.assertTrue(res.matched)
        self.assertIn("exception_chaining", res.signals)

    def test_has_finally_cleanup(self):
        ctx = ASTContext(enclosing_function="process")
        fact = TryFact(
            file_path="/repo/app.py", line=1, handlers=0, has_else=False, has_finally=True,
            context=ctx
        )
        res = self._run_exception([fact], "has_finally_cleanup", fqn="app.process")
        self.assertTrue(res.matched)
        self.assertIn("finally_cleanup", res.signals)

    def test_has_exception_else(self):
        ctx = ASTContext(enclosing_function="process")
        fact = TryFact(
            file_path="/repo/app.py", line=1, handlers=1, has_else=True, has_finally=False,
            context=ctx
        )
        res = self._run_exception([fact], "has_exception_else", fqn="app.process")
        self.assertTrue(res.matched)
        self.assertIn("exception_else", res.signals)

    def test_raises_from_function(self):
        ctx = ASTContext(enclosing_function="process")
        fact = RaiseFact(
            file_path="/repo/app.py", line=1, exception_expression="ValueError()",
            cause=None, context=ctx
        )
        res = self._run_exception([fact], "raises_from_function", fqn="app.process")
        self.assertTrue(res.matched)
        self.assertIn("raises_exception", res.signals)

if __name__ == "__main__":
    unittest.main()

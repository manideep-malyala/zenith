import unittest

from src.analysis.predicates.idioms import IdiomPredicates
from src.core.context import ASTContext
from src.core.models import (
    ComprehensionFact,
    DecoratorFact,
    GeneratorFact,
    LambdaFact,
    WithFact,
)
from src.graph.projections.ast_features import ASTFeatureIndex
from src.resolution.registry import GlobalSymbolRegistry


class TestIdiomPredicates(unittest.TestCase):
    def setUp(self):
        self.registry = GlobalSymbolRegistry("/repo")
        # Mock that file.py belongs to module 'app'
        self.registry._file_to_module = lambda fp: "app"
        
        self.ast_features = ASTFeatureIndex()
        
    def _run_idiom(self, facts, predicate_method, fqn="app.Service.process"):
        self.ast_features.build(facts, self.registry)
        predicates = IdiomPredicates(self.ast_features)
        return getattr(predicates, predicate_method)(fqn)
        
    def test_uses_comprehensions(self):
        ctx = ASTContext(enclosing_class="Service", enclosing_function="process")
        fact = ComprehensionFact(
            file_path="/repo/app.py", line=1, kind="list", 
            generators_count=1, filter_count=0, context=ctx
        )
        res = self._run_idiom([fact], "uses_comprehensions")
        self.assertTrue(res.matched)
        self.assertIn("comprehension", res.signals)
        
    def test_uses_comprehensions_negative(self):
        ctx = ASTContext(enclosing_class="Service", enclosing_function="process")
        # GeneratorFact instead of ComprehensionFact
        fact = GeneratorFact(
            file_path="/repo/app.py", line=1, kind="yield", context=ctx
        )
        res = self._run_idiom([fact], "uses_comprehensions")
        self.assertFalse(res.matched)

    def test_is_generator(self):
        ctx = ASTContext(enclosing_class="Service", enclosing_function="process")
        fact = GeneratorFact(
            file_path="/repo/app.py", line=1, kind="yield", context=ctx
        )
        res = self._run_idiom([fact], "is_generator")
        self.assertTrue(res.matched)
        self.assertIn("generator", res.signals)

    def test_uses_context_managers(self):
        ctx = ASTContext(enclosing_function="process")  # Module level function "app.process"
        fact = WithFact(
            file_path="/repo/app.py", line=1, is_async=False, items_count=1, context=ctx
        )
        res = self._run_idiom([fact], "uses_context_managers", fqn="app.process")
        self.assertTrue(res.matched)
        self.assertIn("context_manager", res.signals)

    def test_uses_lambdas(self):
        ctx = ASTContext(enclosing_function="process")
        fact = LambdaFact(
            file_path="/repo/app.py", line=1, parameters=["x"], defaults_count=0, context=ctx
        )
        res = self._run_idiom([fact], "uses_lambdas", fqn="app.process")
        self.assertTrue(res.matched)
        self.assertIn("lambda", res.signals)

    def test_uses_decorators(self):
        ctx = ASTContext(enclosing_class="Service", enclosing_function="process")
        fact = DecoratorFact(
            file_path="/repo/app.py", line=1, target_name="process", 
            target_type="method", decorator_expression="retry", context=ctx
        )
        res = self._run_idiom([fact], "uses_decorators")
        self.assertTrue(res.matched)
        self.assertIn("decorator", res.signals)

if __name__ == "__main__":
    unittest.main()

import ast
import unittest

from src.analysis.predicates.core import CorePredicates
from src.core.unified import UnifiedFactVisitor
from src.graph.projections.ast_features import ASTFeatureIndex
from src.resolution.registry import GlobalSymbolRegistry


class TestPhase1Core(unittest.TestCase):
    def setUp(self):
        self.registry = GlobalSymbolRegistry(".")
        self.ast_features = ASTFeatureIndex()
        self.predicates = CorePredicates(self.registry, self.ast_features)

    def _parse_and_extract(self, code: str, fqn: str):
        tree = ast.parse(code)
        visitor = UnifiedFactVisitor("test.py", False)
        visitor.visit(tree)
        
        # Populate AST Feature Index manually for test
        self.ast_features._facts_by_fqn.clear()
        
        # We need to map these to the FQN. For testing, we just put all facts under this fqn
        if fqn not in self.ast_features._facts_by_fqn:
            self.ast_features._facts_by_fqn[fqn] = []
            
        self.ast_features._facts_by_fqn[fqn].extend(visitor.definitions)
        self.ast_features._facts_by_fqn[fqn].extend(visitor.exceptions)
        self.ast_features._facts_by_fqn[fqn].extend(visitor.raises)
        self.ast_features._facts_by_fqn[fqn].extend(visitor.lambdas)
        self.ast_features._facts_by_fqn[fqn].extend(visitor.decorators)
        self.ast_features._facts_by_fqn[fqn].extend(visitor.asyncs)
        self.ast_features._facts_by_fqn[fqn].extend(visitor.withs)
        self.ast_features._facts_by_fqn[fqn].extend(visitor.loops)
        self.ast_features._facts_by_fqn[fqn].extend(visitor.conditionals)
        self.ast_features._facts_by_fqn[fqn].extend(visitor.comprehensions)
        self.ast_features._facts_by_fqn[fqn].extend(visitor.generators)
        self.ast_features._facts_by_fqn[fqn].extend(visitor.assignments)
        self.ast_features._facts_by_fqn[fqn].extend(visitor.inheritances)
        self.ast_features._facts_by_fqn[fqn].extend(visitor.returns)

    def test_has_return_annotations(self):
        # Positive
        self._parse_and_extract("def foo() -> int: return 1", "test.foo")
        res = self.predicates.has_return_annotations("test.foo")
        self.assertTrue(res.matched)
        self.assertTrue(len(res.evidence_fact_ids) > 0)
        
        # Negative
        self._parse_and_extract("def bar(): return 1", "test.bar")
        res = self.predicates.has_return_annotations("test.bar")
        self.assertFalse(res.matched)

    def test_has_except_star(self):
        # Edge/Positive (Python 3.11 syntax)
        # Note: ast.parse will only work for except* if run on Python 3.11+
        import sys
        if sys.version_info >= (3, 11):
            self._parse_and_extract("try:\n  pass\nexcept* ValueError:\n  pass", "test.star")
            res = self.predicates.has_except_star("test.star")
            self.assertTrue(res.matched)
            self.assertTrue(len(res.evidence_fact_ids) > 0)

        # Negative
        self._parse_and_extract("try:\n  pass\nexcept ValueError:\n  pass", "test.no_star")
        res = self.predicates.has_except_star("test.no_star")
        self.assertFalse(res.matched)

    def test_has_exception_propagation(self):
        # Positive 1 (raise bare)
        self._parse_and_extract("try:\n  pass\nexcept:\n  raise", "test.prop1")
        res = self.predicates.has_exception_propagation("test.prop1")
        self.assertTrue(res.matched)
        
        # Positive 2 (raise from)
        self._parse_and_extract("try:\n  pass\nexcept Exception as e:\n  raise ValueError() from e", "test.prop2")
        res = self.predicates.has_exception_propagation("test.prop2")
        self.assertTrue(res.matched)
        
        # Negative
        self._parse_and_extract("raise ValueError('foo')", "test.neg")
        res = self.predicates.has_exception_propagation("test.neg")
        self.assertFalse(res.matched)

    def test_has_nested_context_managers(self):
        # Positive
        self._parse_and_extract("with open('a') as a, open('b') as b:\n  pass", "test.nest")
        res = self.predicates.has_nested_context_managers("test.nest")
        self.assertTrue(res.matched)
        
        # Negative
        self._parse_and_extract("with open('a') as a:\n  pass", "test.single")
        res = self.predicates.has_nested_context_managers("test.single")
        self.assertFalse(res.matched)

    def test_uses_nested_functions(self):
        # Positive
        self._parse_and_extract("def outer():\n  def inner():\n    pass\n  pass", "test.outer")
        res = self.predicates.uses_nested_functions("test.outer")
        self.assertTrue(res.matched)
        
        # Negative
        self._parse_and_extract("def func1(): pass\ndef func2(): pass", "test.flat")
        res = self.predicates.uses_nested_functions("test.flat")
        self.assertFalse(res.matched)

if __name__ == "__main__":
    unittest.main()

import ast
import unittest

from src.analysis.predicates.api import ApiPredicates
from src.core.unified import UnifiedFactVisitor
from src.graph.projections.ast_features import ASTFeatureIndex
from src.resolution.registry import GlobalSymbolRegistry


class TestPhase2Api(unittest.TestCase):
    def setUp(self):
        self.registry = GlobalSymbolRegistry(".")
        self.ast_features = ASTFeatureIndex()
        self.predicates = ApiPredicates(self.ast_features, self.registry)

    def _parse_and_extract(self, code: str, fqn: str):
        tree = ast.parse(code)
        visitor = UnifiedFactVisitor("test.py", False)
        visitor.visit(tree)
        
        self.ast_features._facts_by_fqn.clear()
        
        if fqn not in self.ast_features._facts_by_fqn:
            self.ast_features._facts_by_fqn[fqn] = []
            
        self.ast_features._facts_by_fqn[fqn].extend(visitor.imports)
        self.ast_features._facts_by_fqn[fqn].extend(visitor.calls)

    def test_instantiates_type_explicit_import(self):
        code = """
from concurrent.futures import ThreadPoolExecutor
executor = ThreadPoolExecutor()
        """
        self._parse_and_extract(code, "test.func")
        res = self.predicates.instantiates_type("test.func", "concurrent.futures", "ThreadPoolExecutor")
        self.assertTrue(res.matched)
        self.assertTrue(len(res.evidence_fact_ids) > 0)

    def test_instantiates_type_aliased_import(self):
        code = """
import concurrent.futures as cf
executor = cf.ThreadPoolExecutor()
        """
        self._parse_and_extract(code, "test.func")
        res = self.predicates.instantiates_type("test.func", "concurrent.futures", "ThreadPoolExecutor")
        self.assertTrue(res.matched)
        
    def test_calls_api_function_import(self):
        code = """
from requests import get
get('url')
        """
        self._parse_and_extract(code, "test.func")
        res = self.predicates.calls_api("test.func", "requests", "get")
        self.assertTrue(res.matched)

    def test_ambiguous_imports(self):
        code = """
from foo import Client
from bar import Client

Client()
        """
        self._parse_and_extract(code, "test.func")
        # Should resolve to both as possible paths since we don't do deep dataflow
        res_foo = self.predicates.instantiates_type("test.func", "foo", "Client")
        self.assertTrue(res_foo.matched)
        
        res_bar = self.predicates.instantiates_type("test.func", "bar", "Client")
        self.assertTrue(res_bar.matched)

    def test_negative_api_call(self):
        code = """
import concurrent.futures
executor = concurrent.futures.ProcessPoolExecutor()
        """
        self._parse_and_extract(code, "test.func")
        res = self.predicates.instantiates_type("test.func", "concurrent.futures", "ThreadPoolExecutor")
        self.assertFalse(res.matched)

if __name__ == "__main__":
    unittest.main()

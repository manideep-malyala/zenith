import unittest

from src.analysis.predicates.concurrency import ConcurrencyPredicates
from src.analysis.predicates.dependency import DependencyPredicates
from src.core.context import ASTContext
from src.core.models import AsyncFact
from src.graph.models import EdgeType, ResolvedRelationship
from src.graph.projections.ast_features import ASTFeatureIndex
from src.graph.projections.class_dependency import ClassDependencyProjection
from src.resolution.registry import GlobalSymbolRegistry


class TestConcurrencyPredicates(unittest.TestCase):
    def setUp(self):
        self.registry = GlobalSymbolRegistry("/repo")
        self.registry._file_to_module = lambda fp: "app"
        
        self.ast_features = ASTFeatureIndex()
        self.class_deps = ClassDependencyProjection()
        self.dependency = DependencyPredicates(self.class_deps, self.registry)
        
    def _run_concurrency(self, facts, predicate_method, fqn="app.Service.process"):
        self.ast_features.build(facts, self.registry)
        predicates = ConcurrencyPredicates(self.ast_features, self.dependency)
        return getattr(predicates, predicate_method)(fqn)
        
    def test_is_async(self):
        ctx = ASTContext(enclosing_class="Service", enclosing_function="process")
        fact = AsyncFact(
            file_path="/repo/app.py", line=1, kind="await", context=ctx
        )
        res = self._run_concurrency([fact], "is_async")
        self.assertTrue(res.matched)
        self.assertIn("async_await", res.signals)

    def test_uses_thread_pool(self):
        rel = ResolvedRelationship(
            relationship_type=EdgeType.CALLS,
            source_fqn="app.process",
            target_fqn="concurrent.futures.ThreadPoolExecutor",
            resolution_status="RESOLVED",
            resolution_domain="EXTERNAL",
            confidence="HIGH",
            resolution_method="EXPLICIT_IMPORT",
            evidence_fact_ids=[]
        )
        self.class_deps.add_edge("app.process", "concurrent.futures.ThreadPoolExecutor", rel)
        
        predicates = ConcurrencyPredicates(self.ast_features, self.dependency)
        res = predicates.uses_thread_pool("app.process")
        self.assertTrue(res.matched)
        self.assertIn("thread_pool_executor", res.signals)

    def test_uses_process_pool(self):
        rel = ResolvedRelationship(
            relationship_type=EdgeType.CALLS,
            source_fqn="app.process",
            target_fqn="concurrent.futures.process.ProcessPoolExecutor",
            resolution_status="RESOLVED",
            resolution_domain="EXTERNAL",
            confidence="HIGH",
            resolution_method="EXPLICIT_IMPORT",
            evidence_fact_ids=[]
        )
        self.class_deps.add_edge("app.process", "concurrent.futures.process.ProcessPoolExecutor", rel)
        
        predicates = ConcurrencyPredicates(self.ast_features, self.dependency)
        res = predicates.uses_process_pool("app.process")
        self.assertTrue(res.matched)
        self.assertIn("process_pool_executor", res.signals)

    def test_uses_threading_module(self):
        rel = ResolvedRelationship(
            relationship_type=EdgeType.CALLS,
            source_fqn="app.process",
            target_fqn="threading",
            resolution_status="RESOLVED",
            resolution_domain="EXTERNAL",
            confidence="HIGH",
            resolution_method="EXPLICIT_IMPORT",
            evidence_fact_ids=[]
        )
        self.class_deps.add_edge("app.process", "threading", rel)
        
        predicates = ConcurrencyPredicates(self.ast_features, self.dependency)
        res = predicates.uses_threading("app.process")
        self.assertTrue(res.matched)
        self.assertIn("threading_module", res.signals)

    def test_uses_locks(self):
        rel = ResolvedRelationship(
            relationship_type=EdgeType.CALLS,
            source_fqn="app.process",
            target_fqn="threading.Lock",
            resolution_status="RESOLVED",
            resolution_domain="EXTERNAL",
            confidence="HIGH",
            resolution_method="EXPLICIT_IMPORT",
            evidence_fact_ids=[]
        )
        self.class_deps.add_edge("app.process", "threading.Lock", rel)
        
        predicates = ConcurrencyPredicates(self.ast_features, self.dependency)
        res = predicates.uses_locks("app.process")
        self.assertTrue(res.matched)
        self.assertIn("uses_locks", res.signals)

if __name__ == "__main__":
    unittest.main()

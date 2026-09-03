import os
import unittest

from src.analysis.detectors.registry import DetectorRegistry
from src.analysis.predicates.engine import PredicateEngine
from src.catalog.registry import CapabilityRegistry
from src.catalog.resolver import QuestionResolver
from src.core.models import DefinitionFact
from src.graph.projections.builder import ProjectionBuilder
from src.resolution.registry import GlobalSymbolRegistry


class TestQuestionResolver(unittest.TestCase):
    def setUp(self):
        self.cap_registry = CapabilityRegistry()
        yaml_path = os.path.join(
            os.path.dirname(__file__), 
            "../../src/catalog/capabilities.yaml"
        )
        self.cap_registry.load_from_yaml(yaml_path)
        
        self.sym_registry = GlobalSymbolRegistry("/repo")
        self.sym_registry.build([
            DefinitionFact("class", "Service", "app.Service", "/repo/app.py", 1, 10),
            DefinitionFact("method", "execute", "app.Service.execute", "/repo/app.py", 2, 5)
        ])
        
        graphs = ProjectionBuilder().build([], self.sym_registry)
        self.predicates = PredicateEngine(graphs, self.sym_registry)
        self.detectors = DetectorRegistry()
        
        self.resolver = QuestionResolver(
            self.cap_registry,
            self.predicates,
            self.detectors,
            self.sym_registry,
            []
        )

    def test_normalize_query_lambda(self):
        concept, op = self.resolver._normalize_query("Where are lambdas used?")
        self.assertEqual(concept, "lambdas")
        self.assertEqual(op.value, "LOCATE")

    def test_normalize_query_thread_pool(self):
        concept, op = self.resolver._normalize_query("How many thread pools exist?")
        self.assertEqual(concept, "threadpoolexecutor")
        self.assertEqual(op.value, "COUNT")
        
    def test_resolve_lambda_query(self):
        # Even with no evidence, it should return an EvidencePackage
        pkg = self.resolver.resolve("Where are lambdas used?")
        self.assertEqual(pkg.concept, "lambdas")
        self.assertEqual(pkg.operation, "LOCATE")
        self.assertEqual(pkg.summary.get("occurrences"), 0)
        self.assertEqual(len(pkg.evidence), 0)

if __name__ == "__main__":
    unittest.main()

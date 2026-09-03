import os
import tempfile
import unittest
from textwrap import dedent

from src.analysis.predicates.engine import PredicateEngine
from src.core.models import DefinitionFact
from src.graph.models import EdgeType, ResolvedRelationship
from src.graph.projections.builder import ProjectionBuilder
from src.resolution.registry import GlobalSymbolRegistry


class RemainingPredicatesTests(unittest.TestCase):
    def setUp(self):
        self.registry = GlobalSymbolRegistry("/repo")

    def test_has_method_overrides_positive(self):
        defs = [
            DefinitionFact("class", "Base", "Base", "/repo/app.py", 1, 3),
            DefinitionFact("method", "run", "Base.run", "/repo/app.py", 2, 3),
            DefinitionFact("class", "Child", "Child", "/repo/app.py", 5, 7),
            DefinitionFact("method", "run", "Child.run", "/repo/app.py", 6, 7),
        ]
        self.registry.build(defs)

        rels = [
            ResolvedRelationship(
                relationship_type=EdgeType.INHERITS,
                source_fqn="app.Child",
                target_fqn="app.Base",
                resolution_status="RESOLVED",
                resolution_domain="LOCAL",
                confidence="HIGH",
                resolution_method="SAME_FILE",
                evidence_fact_ids=["fact-inherits"],
            )
        ]

        graphs = ProjectionBuilder().build(rels, self.registry)
        engine = PredicateEngine(graphs, self.registry)

        result = engine.inheritance.has_method_overrides("app.Child")
        self.assertTrue(result.matched)
        self.assertEqual(result.confidence, "HIGH")
        self.assertIn("method_overrides", result.signals)
        self.assertTrue(len(result.evidence_edge_ids) > 0)
        self.assertIn("overrides methods: ['run']", result.explanation)

    def test_has_method_overrides_negative(self):
        defs = [
            DefinitionFact("class", "Base", "Base", "/repo/app.py", 1, 3),
            DefinitionFact("method", "base_run", "Base.base_run", "/repo/app.py", 2, 3),
            DefinitionFact("class", "Child", "Child", "/repo/app.py", 5, 7),
            DefinitionFact("method", "child_run", "Child.child_run", "/repo/app.py", 6, 7),
        ]
        self.registry.build(defs)

        rels = [
            ResolvedRelationship(
                relationship_type=EdgeType.INHERITS,
                source_fqn="app.Child",
                target_fqn="app.Base",
                resolution_status="RESOLVED",
                resolution_domain="LOCAL",
                confidence="HIGH",
                resolution_method="SAME_FILE",
                evidence_fact_ids=["fact-inherits"],
            )
        ]

        graphs = ProjectionBuilder().build(rels, self.registry)
        engine = PredicateEngine(graphs, self.registry)

        result = engine.inheritance.has_method_overrides("app.Child")
        self.assertFalse(result.matched)

    def test_has_method_overrides_edge_no_ancestors(self):
        defs = [
            DefinitionFact("class", "Base", "Base", "/repo/app.py", 1, 3),
            DefinitionFact("method", "run", "Base.run", "/repo/app.py", 2, 3),
        ]
        self.registry.build(defs)
        graphs = ProjectionBuilder().build([], self.registry)
        engine = PredicateEngine(graphs, self.registry)

        result = engine.inheritance.has_method_overrides("app.Base")
        self.assertFalse(result.matched)
        self.assertIn("has no local ancestors", result.explanation)

    def test_has_constructor_injection_positive(self):
        with tempfile.NamedTemporaryFile("w", delete=False, suffix=".py") as f:
            f.write(dedent("""
                class Service:
                    def __init__(self, repo: Repository):
                        self.repo = repo
            """))
            tmp_path = f.name

        defs = [
            DefinitionFact("class", "Service", "Service", tmp_path, 2, 4),
            DefinitionFact("method", "__init__", "Service.__init__", tmp_path, 3, 4),
            DefinitionFact("class", "Repository", "app.Repository", "/repo/app.py", 1, 2),
        ]
        
        # In setup with temp_path, registry needs project root matching
        registry = GlobalSymbolRegistry(os.path.dirname(tmp_path))
        registry.build(defs)

        # FQN will be the module name of the temp file
        module_name = os.path.basename(tmp_path)[:-3]
        class_fqn = f"{module_name}.Service"

        rels = [
            ResolvedRelationship(
                relationship_type=EdgeType.COMPOSES,
                source_fqn=class_fqn,
                target_fqn="app.Repository",
                resolution_status="RESOLVED",
                resolution_domain="LOCAL",
                confidence="HIGH",
                resolution_method="SAME_FILE",
                evidence_fact_ids=["fact-comp"],
            )
        ]

        graphs = ProjectionBuilder().build(rels, registry)
        engine = PredicateEngine(graphs, registry)

        result = engine.dependency.has_constructor_injection(class_fqn)
        self.assertTrue(result.matched)
        self.assertEqual(result.confidence, "HIGH")
        self.assertIn("constructor_injection", result.signals)

    def test_has_constructor_injection_negative(self):
        with tempfile.NamedTemporaryFile("w", delete=False, suffix=".py") as f:
            f.write(dedent("""
                class Service:
                    def __init__(self):
                        self.repo = Repository()
            """))
            tmp_path = f.name

        defs = [
            DefinitionFact("class", "Service", "Service", tmp_path, 2, 4),
            DefinitionFact("method", "__init__", "Service.__init__", tmp_path, 3, 4),
            DefinitionFact("class", "Repository", "app.Repository", "/repo/app.py", 1, 2),
        ]
        
        registry = GlobalSymbolRegistry(os.path.dirname(tmp_path))
        registry.build(defs)
        
        module_name = os.path.basename(tmp_path)[:-3]
        class_fqn = f"{module_name}.Service"

        rels = [
            ResolvedRelationship(
                relationship_type=EdgeType.COMPOSES,
                source_fqn=class_fqn,
                target_fqn="app.Repository",
                resolution_status="RESOLVED",
                resolution_domain="LOCAL",
                confidence="HIGH",
                resolution_method="SAME_FILE",
                evidence_fact_ids=["fact-comp"],
            )
        ]

        graphs = ProjectionBuilder().build(rels, registry)
        engine = PredicateEngine(graphs, registry)

        result = engine.dependency.has_constructor_injection(class_fqn)
        self.assertFalse(result.matched)
        self.assertIn("takes no parameters", result.explanation)

if __name__ == "__main__":
    unittest.main()

import os
import tempfile
import unittest
from textwrap import dedent

from src.analysis.detectors.base import DetectionContext
from src.analysis.detectors.patterns.dependency_injection import (
    DependencyInjectionDetector,
)
from src.analysis.detectors.patterns.srp_risk import SRPRiskDetector
from src.analysis.detectors.patterns.strategy import StrategyDetector
from src.analysis.predicates.engine import PredicateEngine
from src.core.models import Confidence, DefinitionFact
from src.graph.models import EdgeType, ResolvedRelationship
from src.graph.projections.builder import ProjectionBuilder
from src.resolution.registry import GlobalSymbolRegistry


class DetectorProofLayerTests(unittest.TestCase):
    def _run_detector(self, detector, rels, defs, file_path=None):
        registry = GlobalSymbolRegistry(os.path.dirname(file_path) if file_path else "/repo")
        registry.build(defs)
        
        graphs = ProjectionBuilder().build(rels, registry)
        engine = PredicateEngine(graphs, registry)
        
        rel_ids = frozenset(r.relationship_id for r in rels)
        context = DetectionContext(engine, registry, rel_ids, tuple(rels))
        
        return detector.detect(context)

    # ==========================
    # 1. Dependency Injection
    # ==========================
    def test_di_strong_positive_typed_abstraction(self):
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
        
        module_name = os.path.basename(tmp_path)[:-3]
        class_fqn = f"{module_name}.Service"
        
        rels = [
            ResolvedRelationship(EdgeType.COMPOSES, class_fqn, "app.Repository", "RESOLVED", "LOCAL", "HIGH", "SAME_FILE", ["f1"]),
            ResolvedRelationship(EdgeType.CALLS, class_fqn, "app.Repository", "RESOLVED", "LOCAL", "HIGH", "SAME_FILE", ["f2"]),
        ]
        
        findings = self._run_detector(DependencyInjectionDetector(), rels, defs, tmp_path)
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0].confidence, Confidence.HIGH)
        self.assertIn("injects abstract dependencies", findings[0].explanation)
        self.assertEqual(findings[0].finding_type, "INFERENCE")

    def test_di_untyped_dependency_weaker_confidence(self):
        with tempfile.NamedTemporaryFile("w", delete=False, suffix=".py") as f:
            f.write(dedent("""
                class Service:
                    def __init__(self, repo):
                        self.repo = repo
            """))
            tmp_path = f.name

        defs = [
            DefinitionFact("class", "Service", "Service", tmp_path, 2, 4),
            DefinitionFact("method", "__init__", "Service.__init__", tmp_path, 3, 4),
        ]
        
        # No COMPOSES edge because it's untyped
        rels = []
        
        findings = self._run_detector(DependencyInjectionDetector(), rels, defs, tmp_path)
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0].confidence, Confidence.LOW)
        self.assertIn("untyped", findings[0].explanation)

    def test_di_strong_negative_self_construction(self):
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
        
        module_name = os.path.basename(tmp_path)[:-3]
        class_fqn = f"{module_name}.Service"
        
        rels = [
            ResolvedRelationship(EdgeType.COMPOSES, class_fqn, "app.Repository", "RESOLVED", "LOCAL", "HIGH", "SAME_FILE", ["f1"]),
        ]
        
        findings = self._run_detector(DependencyInjectionDetector(), rels, defs, tmp_path)
        self.assertEqual(len(findings), 0)

    # ==========================
    # 2. Strategy
    # ==========================
    def test_strategy_inheritance_based(self):
        defs = [
            DefinitionFact("class", "Context", "Context", "/repo/app.py", 1, 3),
            DefinitionFact("class", "BaseStrategy", "BaseStrategy", "/repo/app.py", 5, 6),
            DefinitionFact("class", "StrategyA", "StrategyA", "/repo/app.py", 8, 9),
            DefinitionFact("class", "StrategyB", "StrategyB", "/repo/app.py", 11, 12),
            DefinitionFact("method", "run", "BaseStrategy.run", "/repo/app.py", 6, 6),
            DefinitionFact("method", "run", "StrategyA.run", "/repo/app.py", 9, 9),
        ]
        rels = [
            ResolvedRelationship(EdgeType.COMPOSES, "app.Context", "app.BaseStrategy", "RESOLVED", "LOCAL", "HIGH", "SAME_FILE", ["f1"]),
            ResolvedRelationship(EdgeType.CALLS, "app.Context", "app.BaseStrategy", "RESOLVED", "LOCAL", "HIGH", "SAME_FILE", ["f2"]),
            ResolvedRelationship(EdgeType.INHERITS, "app.StrategyA", "app.BaseStrategy", "RESOLVED", "LOCAL", "HIGH", "SAME_FILE", ["f3"]),
            ResolvedRelationship(EdgeType.INHERITS, "app.StrategyB", "app.BaseStrategy", "RESOLVED", "LOCAL", "HIGH", "SAME_FILE", ["f4"]),
        ]
        findings = self._run_detector(StrategyDetector(), rels, defs)
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0].confidence, Confidence.HIGH)
        self.assertIn("app.BaseStrategy", findings[0].explanation)
        self.assertEqual(findings[0].finding_type, "INFERENCE")

    def test_strategy_composition_based_no_inheritance(self):
        defs = [
            DefinitionFact("class", "Context", "Context", "/repo/app.py", 1, 3),
            DefinitionFact("class", "StrategyIntf", "StrategyIntf", "/repo/app.py", 5, 6),
        ]
        rels = [
            ResolvedRelationship(EdgeType.COMPOSES, "app.Context", "app.StrategyIntf", "RESOLVED", "LOCAL", "HIGH", "SAME_FILE", ["f1"]),
            ResolvedRelationship(EdgeType.CALLS, "app.Context", "app.StrategyIntf", "RESOLVED", "LOCAL", "HIGH", "SAME_FILE", ["f2"]),
        ]
        # Ambiguous / weak strategy since no inheritance or overrides are observed.
        findings = self._run_detector(StrategyDetector(), rels, defs)
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0].confidence, Confidence.LOW)
        self.assertNotIn("interchangeable implementations", findings[0].explanation)

    def test_strategy_strong_negative(self):
        defs = [
            DefinitionFact("class", "Context", "Context", "/repo/app.py", 1, 3),
            DefinitionFact("class", "Helper", "Helper", "/repo/app.py", 5, 6),
        ]
        # Context composes Helper, but DOES NOT call it (no delegation)
        rels = [
            ResolvedRelationship(EdgeType.COMPOSES, "app.Context", "app.Helper", "RESOLVED", "LOCAL", "HIGH", "SAME_FILE", ["f1"]),
        ]
        findings = self._run_detector(StrategyDetector(), rels, defs)
        self.assertEqual(len(findings), 0)

    # ==========================
    # 3. SRP Risk
    # ==========================
    def test_srp_high_fan_out_unrelated(self):
        # 5+ dependencies, 5+ methods, 3+ diverse modules -> RISK
        defs = [DefinitionFact("class", "GodClass", "GodClass", "/repo/app.py", 1, 20)]
        for i in range(5):
            defs.append(DefinitionFact("method", f"m{i}", f"GodClass.m{i}", "/repo/app.py", i+2, i+2))
            
        for i in range(5):
            defs.append(DefinitionFact("class", f"Dep{i}", f"Dep{i}", f"/repo/mod{i}.py", 1, 2))
            
        rels = [
            ResolvedRelationship(EdgeType.CALLS, "app.GodClass", f"mod{i}.Dep{i}", "RESOLVED", "LOCAL", "HIGH", "SAME_FILE", ["f"])
            for i in range(5)
        ]
        findings = self._run_detector(SRPRiskDetector(), rels, defs)
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0].finding_type, "RISK_INDICATOR")
        self.assertEqual(findings[0].confidence, Confidence.LOW)

    def test_srp_high_fan_out_coherent(self):
        # 5+ dependencies, 5+ methods, but all in the same module -> NO RISK (not enough diversity)
        defs = [DefinitionFact("class", "OrderSvc", "OrderSvc", "/repo/app.py", 1, 20)]
        for i in range(5):
            defs.append(DefinitionFact("method", f"m{i}", f"OrderSvc.m{i}", "/repo/app.py", i+2, i+2))
            
        for i in range(5):
            defs.append(DefinitionFact("class", f"Dep{i}", f"Dep{i}", "/repo/modA.py", 1, 2))
            
        rels = [
            ResolvedRelationship(EdgeType.CALLS, "app.OrderSvc", f"modA.Dep{i}", "RESOLVED", "LOCAL", "HIGH", "SAME_FILE", ["f"])
            for i in range(5)
        ]
        findings = self._run_detector(SRPRiskDetector(), rels, defs)
        self.assertEqual(len(findings), 0)

if __name__ == "__main__":
    unittest.main()

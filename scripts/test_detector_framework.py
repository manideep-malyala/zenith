import unittest
from src.core.models import Confidence
from src.analysis.detectors.models import Finding
from src.analysis.detectors.base import BaseDetector, DetectionContext
from src.analysis.detectors.registry import DetectorRegistry
from src.analysis.detectors.engine import DetectionEngine
from src.analysis.detectors.evidence import validate_finding_evidence
from src.analysis.predicates.engine import PredicateEngine
from src.analysis.predicates.models import PredicateResult
from src.graph.projections.models import GraphProjections
from src.graph.projections.class_dependency import ClassDependencyProjection
from src.graph.projections.inheritance import InheritanceProjection
from src.graph.projections.module_coupling import ModuleCouplingProjection
from src.resolution.registry import GlobalSymbolRegistry
from src.graph.models import ResolvedRelationship, EdgeType

class MockPolymorphicDetector(BaseDetector):
    detector_id = "test_poly"
    pattern_name = "Polymorphic Family"
    category = "STRUCTURAL"

    def detect(self, context: DetectionContext) -> list[Finding]:
        findings = []
        # Mock checking all classes in registry for polymorphic family
        for class_fqn in ["base.Class", "other.Class"]:
            if class_fqn == "base.Class":
                findings.append(
                    Finding(
                        detector_id=self.detector_id,
                        pattern_name=self.pattern_name,
                        category=self.category,
                        subject_fqn=class_fqn,
                        confidence=Confidence.HIGH,
                        evidence_relationship_ids=["rel1", "rel2"],
                        explanation="Has multiple children",
                        related_fqns=["child.A", "child.B"]
                    )
                )
        return findings

class MockDuplicateDetector(BaseDetector):
    detector_id = "test_dup"
    pattern_name = "Duplicate Emitter"
    category = "TEST"

    def detect(self, context: DetectionContext) -> list[Finding]:
        f1 = Finding(
            detector_id=self.detector_id,
            pattern_name=self.pattern_name,
            category=self.category,
            subject_fqn="test.Subject",
            confidence=Confidence.HIGH,
            evidence_relationship_ids=["rel1"],
            explanation="Same finding",
            related_fqns=[]
        )
        f2 = Finding(
            detector_id=self.detector_id,
            pattern_name=self.pattern_name,
            category=self.category,
            subject_fqn="test.Subject",
            confidence=Confidence.HIGH,
            evidence_relationship_ids=["rel1"], # same evidence
            explanation="Same finding but emitted again",
            related_fqns=[]
        )
        return [f1, f2]

class TestDetectorFramework(unittest.TestCase):
    def setUp(self):
        self.registry = DetectorRegistry()
        self.engine = DetectionEngine(self.registry)
        
        projections = GraphProjections(
            class_dependencies=ClassDependencyProjection(),
            inheritance=InheritanceProjection(),
            module_coupling=ModuleCouplingProjection()
        )
        symbol_registry = GlobalSymbolRegistry("/fake")
        self.predicates = PredicateEngine(projections, symbol_registry)

    def test_registry_registration_and_order(self):
        d2 = MockDuplicateDetector()
        d1 = MockPolymorphicDetector()
        self.registry.register(d2)
        self.registry.register(d1)
        
        detectors = self.registry.all()
        # Should be ordered by detector_id: 'test_dup', 'test_poly'
        self.assertEqual(len(detectors), 2)
        self.assertEqual(detectors[0].detector_id, "test_dup")
        self.assertEqual(detectors[1].detector_id, "test_poly")

    def test_finding_determinism_and_hashing(self):
        f1 = Finding(
            detector_id="d1",
            pattern_name="p1",
            category="c1",
            subject_fqn="s1",
            confidence=Confidence.HIGH,
            evidence_relationship_ids=["r2", "r1"],
            explanation="e1",
            related_fqns=["fqn2", "fqn1"]
        )
        
        f2 = Finding(
            detector_id="d1",
            pattern_name="p1",
            category="c1",
            subject_fqn="s1",
            confidence=Confidence.HIGH,
            evidence_relationship_ids=["r1", "r2"], # different order
            explanation="different explanation doesn't change hash",
            related_fqns=["fqn1", "fqn2"]
        )
        
        self.assertEqual(f1.finding_id, f2.finding_id)
        self.assertEqual(f1.evidence_relationship_ids, ("r1", "r2"))
        self.assertEqual(f1.related_fqns, ("fqn1", "fqn2"))

    def test_evidence_validation(self):
        f1 = Finding("d1", "p1", "c1", "s1", Confidence.HIGH, ["valid1"], "exp")
        self.assertTrue(validate_finding_evidence(f1, {"valid1", "valid2"}))
        
        # Invalid evidence
        f2 = Finding("d1", "p1", "c1", "s1", Confidence.HIGH, ["valid1", "invalid3"], "exp")
        self.assertFalse(validate_finding_evidence(f2, {"valid1", "valid2"}))
        
        # No evidence
        f3 = Finding("d1", "p1", "c1", "s1", Confidence.HIGH, [], "exp")
        self.assertFalse(validate_finding_evidence(f3, {"valid1"}))

    def test_engine_execution_and_deduplication(self):
        self.registry.register(MockDuplicateDetector())
        self.registry.register(MockPolymorphicDetector())
        
        # Provide valid relationship ids to pass validation
        relationships = [
            ResolvedRelationship(EdgeType.CALLS, "a", "b", "RESOLVED", "LOCAL", "HIGH", "EXPLICIT_IMPORT", []),
            ResolvedRelationship(EdgeType.CALLS, "c", "d", "RESOLVED", "LOCAL", "HIGH", "EXPLICIT_IMPORT", []),
        ]
        # mock the relationships objects id
        relationships[0].relationship_id = "rel1"
        relationships[1].relationship_id = "rel2"

        findings = self.engine.run(self.predicates, GlobalSymbolRegistry("/fake"), relationships)
        
        # Total findings should be 2 (1 from duplicate after deduplication, 1 from polymorphic)
        self.assertEqual(len(findings), 2)
        
        # Should be canonically sorted by pattern_name: "Duplicate Emitter", "Polymorphic Family"
        self.assertEqual(findings[0].pattern_name, "Duplicate Emitter")
        self.assertEqual(findings[1].pattern_name, "Polymorphic Family")

if __name__ == "__main__":
    unittest.main()

from src.analysis.detectors.base import BaseDetector, DetectionContext
from src.analysis.detectors.models import Finding


class SingletonDetector(BaseDetector):
    """
    Detects the Singleton pattern heuristically.
    Signals:
    - Overrides __new__ to return a stored instance.
    - Class-level attribute to store the instance (e.g. _instance).
    """
    
    detector_id = "singleton"
    pattern_name = "Singleton"
    category = "CREATIONAL"

    def detect(self, context: DetectionContext) -> list[Finding]:
        findings = []
        # Find all classes that override __new__
        for fqn, defn in context.registry.definitions_by_fqn.items():
            if defn.definition_type == "class":
                if self._has_singleton_new(fqn, context):
                    findings.append(Finding(
                        detector_id=self.detector_id,
                        pattern_name=self.pattern_name,
                        category=self.category,
                        subject_fqn=fqn,
                        confidence="MEDIUM",
                        finding_type="HEURISTIC",
                        evidence_relationship_ids=[],
                        explanation="Class implements __new__, typical of Singleton."
                    ))
        return findings

    def _has_singleton_new(self, class_fqn: str, context: DetectionContext) -> bool:
        new_fqn = f"{class_fqn}.__new__"
        return new_fqn in context.registry.definitions_by_fqn

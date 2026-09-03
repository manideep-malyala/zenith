
from src.analysis.detectors.base import BaseDetector, DetectionContext
from src.analysis.detectors.models import Finding


class FactoryMethodDetector(BaseDetector):
    """
    Detects the Factory Method pattern.
    Signals:
    - A method returns an instantiated object (usually not its own class).
    - Or named like 'create_*', 'make_*', 'build_*', '*_factory'.
    """
    
    detector_id = "factory_method"
    pattern_name = "Factory Method"
    category = "CREATIONAL"

    def detect(self, context: DetectionContext) -> list[Finding]:
        findings = []
        
        # A simple heuristic: find methods with 'create', 'make', 'build' or 'factory' in their name
        # that instantiate objects.
        for fqn, defn in context.registry.definitions_by_fqn.items():
            if defn.definition_type in ("method", "function"):
                name = defn.name.lower()
                if any(kw in name for kw in ["create_", "make_", "build_", "_factory", "factory_"]):
                    # To be safer, we could check if it instantiates something, but naming convention is strong.
                    findings.append(Finding(
                        detector_id=self.detector_id,
                        pattern_name=self.pattern_name,
                        category=self.category,
                        subject_fqn=fqn,
                        confidence="MEDIUM",
                        finding_type="HEURISTIC",
                        evidence_relationship_ids=[],
                        explanation=f"Naming convention '{defn.name}' indicates a Factory method."
                    ))
                    
        return findings

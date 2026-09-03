from src.analysis.detectors.base import BaseDetector, DetectionContext
from src.analysis.detectors.models import Finding
from src.core.models import Confidence


class DependencyInjectionDetector(BaseDetector):
    detector_id = "dependency_injection"
    pattern_name = "Dependency Injection"
    category = "STRUCTURAL"

    def detect(self, context: DetectionContext) -> list[Finding]:
        findings: list[Finding] = []
        dependency = context.predicates.dependency

        # Context -> Strategy
        all_classes = {
            fqn for fqn, defn in context.registry.definitions_by_fqn.items()
            if defn.definition_type == "class"
        }

        for class_fqn in all_classes:
            has_injection = dependency.has_constructor_injection(class_fqn)
            if not has_injection.matched:
                continue

            # We know it has constructor injection (either typed or untyped).
            # Let's check dependencies for abstraction.
            deps = dependency.dependencies_of(class_fqn)
            
            # Identify the injected dependencies
            # We don't have perfect alignment of param -> target, but we can check if it depends on an abstraction
            di_targets = []
            abstraction_targets = []
            
            evidence_ids = set(has_injection.evidence_relationship_ids)
            
            for target in deps:
                comp = dependency.composes(class_fqn, target)
                if comp.matched:
                    di_targets.append(target)
                    abs_dep = dependency.depends_on_abstraction(class_fqn, target)
                    if abs_dep.matched:
                        abstraction_targets.append(target)
                        evidence_ids.update(abs_dep.evidence_relationship_ids)
                        
            if not di_targets and "untyped_parameter" not in has_injection.signals:
                continue
                
            evidence_ids &= context.valid_relationship_ids
            
            confidence = Confidence.LOW
            explanation = f"{class_fqn} uses constructor injection."
            if abstraction_targets:
                confidence = Confidence.HIGH
                explanation += f" It injects abstract dependencies: {', '.join(abstraction_targets)}."
            elif di_targets:
                confidence = Confidence.MEDIUM
                explanation += f" It injects concrete dependencies: {', '.join(di_targets)}."
            else:
                confidence = Confidence.LOW
                explanation += " The injected dependencies are untyped."

            findings.append(Finding(
                detector_id=self.detector_id,
                pattern_name=self.pattern_name,
                category=self.category,
                subject_fqn=class_fqn,
                confidence=confidence,
                finding_type="INFERENCE",
                evidence_relationship_ids=evidence_ids,
                explanation=explanation,
                related_fqns=di_targets,
            ))

        return findings

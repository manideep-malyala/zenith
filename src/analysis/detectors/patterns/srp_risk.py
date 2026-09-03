from src.analysis.detectors.base import BaseDetector, DetectionContext
from src.analysis.detectors.models import Finding
from src.core.models import Confidence
from src.graph.projections.normalization import owner_module


class SRPRiskDetector(BaseDetector):
    detector_id = "srp_risk"
    pattern_name = "SRP Risk Indicator"
    category = "RISK"

    def detect(self, context: DetectionContext) -> list[Finding]:
        findings: list[Finding] = []
        dependency = context.predicates.dependency

        all_classes = {
            fqn for fqn, defn in context.registry.definitions_by_fqn.items()
            if defn.definition_type == "class"
        }

        for class_fqn in all_classes:
            deps = dependency.dependencies_of(class_fqn)
            fan_out = len(deps)
            
            # High fan-out
            if fan_out < 5:
                continue
                
            # High method count
            methods = [
                d for fqn, d in context.registry.definitions_by_fqn.items()
                if d.definition_type == "method" and fqn.startswith(class_fqn + ".") and fqn.count(".") == class_fqn.count(".") + 1
            ]
            method_count = len(methods)
            if method_count < 5:
                continue

            # High dependency diversity (number of unique target modules)
            unique_modules = set()
            for dep in deps:
                mod = owner_module(dep, context.registry)
                if mod:
                    unique_modules.add(mod)
                    
            # A highly diverse class touches 3+ different modules/layers
            if len(unique_modules) < 3:
                continue

            # Collect evidence (all outgoing edges)
            evidence_ids = set()
            for dep in deps:
                evidence_ids.update(dependency._evidence_ids(class_fqn, dep))
                
            evidence_ids &= context.valid_relationship_ids

            findings.append(Finding(
                detector_id=self.detector_id,
                pattern_name=self.pattern_name,
                category=self.category,
                subject_fqn=class_fqn,
                confidence=Confidence.LOW,  # Explicitly LOW until we have deep cohesion analysis
                finding_type="RISK_INDICATOR",
                evidence_relationship_ids=evidence_ids,
                explanation=(
                    f"{class_fqn} exhibits multiple signals of an SRP risk: "
                    f"high fan-out ({fan_out} dependencies), "
                    f"high method count ({method_count} methods), and "
                    f"high dependency diversity (touches {len(unique_modules)} different modules). "
                    f"These structural metrics suggest potential responsibility diversity, "
                    f"but true cohesion analysis is required for higher confidence."
                ),
                related_fqns=list(deps),
            ))

        return findings

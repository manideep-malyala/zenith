
from src.analysis.predicates.engine import PredicateEngine
from src.graph.models import ResolvedRelationship
from src.resolution.registry import GlobalSymbolRegistry

from .base import DetectionContext
from .evidence import validate_finding_evidence
from .models import Finding
from .registry import DetectorRegistry


class DetectionEngine:
    def __init__(self, registry: DetectorRegistry):
        self.registry = registry

    def run(
        self,
        predicates: PredicateEngine,
        symbol_registry: GlobalSymbolRegistry,
        relationships: list[ResolvedRelationship]
    ) -> list[Finding]:
        valid_relationship_ids = frozenset(r.relationship_id for r in relationships)
        
        context = DetectionContext(
            predicates=predicates,
            registry=symbol_registry,
            valid_relationship_ids=valid_relationship_ids,
            relationships=tuple(relationships),
        )

        all_findings = []
        for detector in self.registry.all():
            findings = detector.detect(context)
            all_findings.extend(findings)

        # Validate evidence
        valid_findings = []
        for finding in all_findings:
            if validate_finding_evidence(finding, valid_relationship_ids):
                valid_findings.append(finding)

        # Deduplicate
        unique_findings: dict[str, Finding] = {}
        for finding in valid_findings:
            if finding.finding_id not in unique_findings:
                unique_findings[finding.finding_id] = finding

        # Canonical sort (by pattern name, then subject FQN, then finding ID)
        sorted_findings = sorted(
            unique_findings.values(),
            key=lambda f: (f.pattern_name, f.subject_fqn, f.finding_id)
        )

        return sorted_findings

"""
Composite Pattern Detector

Structural signature:
  Component (base class with >= 2 children)
    ├── Composite: inherits Component AND composes Component
    └── Leaf:     inherits Component AND does NOT compose Component

One finding is emitted per (Component, composite_node, leaf_node) tuple.
  subject_fqn  = Component
  related_fqns = (composite_node, leaf_node)

Confidence:
  HIGH   — all evidence relationships are RESOLVED + LOCAL + confidence=HIGH
  MEDIUM — any evidence is PARTIAL or has lower confidence
"""

from src.analysis.detectors.base import BaseDetector, DetectionContext
from src.analysis.detectors.models import Finding
from src.core.models import Confidence


def _evidence_confidence(evidence_ids: set[str], context: DetectionContext) -> Confidence:
    """Derive confidence from the provenance of all supporting relationships."""
    for rel_id in evidence_ids:
        rel = context.get_relationship(rel_id)
        if rel is None:
            return Confidence.MEDIUM
        if rel.resolution_status != "RESOLVED" or rel.resolution_domain != "LOCAL" or rel.confidence != "HIGH":
            return Confidence.MEDIUM
    return Confidence.HIGH


class CompositeDetector(BaseDetector):
    detector_id = "composite"
    pattern_name = "Composite"
    category = "STRUCTURAL"

    def detect(self, context: DetectionContext) -> list[Finding]:
        findings: list[Finding] = []
        inheritance = context.predicates.inheritance
        composition = context.predicates.composition

        all_nodes: set[str] = set(inheritance.projection.nodes())

        for component in all_nodes:
            # Prerequisite: polymorphic family (>= 2 direct children)
            poly = inheritance.is_polymorphic_family(component)
            if not poly.matched:
                continue

            children = inheritance.projection.children_of(component)
            composites: set[str] = set()
            leaves: set[str] = set()

            for child in children:
                if composition.is_composed_of(child, component).matched:
                    composites.add(child)
                else:
                    leaves.add(child)

            # Must have at least one Composite AND one Leaf to confirm structure
            if not composites or not leaves:
                continue

            # Collect all supporting evidence IDs
            evidence_ids: set[str] = set(poly.evidence_relationship_ids)
            for child in children:
                inh = inheritance.inherits_from(child, component)
                evidence_ids.update(inh.evidence_relationship_ids)
            for composite_node in composites:
                comp_r = composition.is_composed_of(composite_node, component)
                evidence_ids.update(comp_r.evidence_relationship_ids)

            # Filter to only valid relationship IDs known to the engine
            evidence_ids &= context.valid_relationship_ids
            if not evidence_ids:
                continue

            confidence = _evidence_confidence(evidence_ids, context)

            # Emit one finding per (Composite, Leaf) pair
            for composite_node in sorted(composites):
                for leaf_node in sorted(leaves):
                    findings.append(Finding(
                        detector_id=self.detector_id,
                        pattern_name=self.pattern_name,
                        category=self.category,
                        subject_fqn=component,
                        confidence=confidence,
                        finding_type="OBSERVED",
                        evidence_relationship_ids=evidence_ids,
                        explanation=(
                            f"{component} acts as the Component. "
                            f"{composite_node} is a Composite node (inherits and composes {component}). "
                            f"{leaf_node} is a Leaf node (inherits but does not compose {component})."
                        ),
                        related_fqns=[composite_node, leaf_node],
                    ))

        return findings

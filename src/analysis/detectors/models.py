import hashlib
from collections.abc import Iterable
from dataclasses import dataclass, field

from src.core.models import Confidence


@dataclass(frozen=True)
class Finding:
    finding_id: str = field(init=False)
    detector_id: str
    pattern_name: str
    category: str
    subject_fqn: str
    confidence: Confidence
    finding_type: str  # "OBSERVED", "INFERENCE", "RISK_INDICATOR"
    evidence_relationship_ids: tuple[str, ...]
    explanation: str
    related_fqns: tuple[str, ...] = field(default_factory=tuple)

    def __init__(
        self,
        detector_id: str,
        pattern_name: str,
        category: str,
        subject_fqn: str,
        confidence: Confidence,
        finding_type: str,
        evidence_relationship_ids: Iterable[str],
        explanation: str,
        related_fqns: Iterable[str] = ()
    ):
        object.__setattr__(self, 'detector_id', detector_id)
        object.__setattr__(self, 'pattern_name', pattern_name)
        object.__setattr__(self, 'category', category)
        object.__setattr__(self, 'subject_fqn', subject_fqn)
        object.__setattr__(self, 'confidence', confidence)
        object.__setattr__(self, 'finding_type', finding_type)
        object.__setattr__(self, 'explanation', explanation)
        
        # Enforce canonical ordering
        sorted_evidence = tuple(sorted(set(evidence_relationship_ids)))
        sorted_related = tuple(sorted(set(related_fqns)))
        
        object.__setattr__(self, 'evidence_relationship_ids', sorted_evidence)
        object.__setattr__(self, 'related_fqns', sorted_related)
        
        # Compute deterministic finding_id
        # SHA256(detector_id | pattern_name | subject_fqn | sorted(related_fqns))
        hash_input = f"{detector_id}|{pattern_name}|{subject_fqn}|{'|'.join(sorted_related)}"
        finding_id = hashlib.sha256(hash_input.encode("utf-8")).hexdigest()
        object.__setattr__(self, 'finding_id', finding_id)

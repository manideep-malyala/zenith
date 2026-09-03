from collections.abc import Iterable
from dataclasses import dataclass, field


@dataclass(frozen=True)
class PredicateResult:
    matched: bool
    confidence: str = "LOW"
    signals: tuple[str, ...] = field(default_factory=tuple)
    evidence_fact_ids: tuple[str, ...] = field(default_factory=tuple)
    evidence_edge_ids: tuple[str, ...] = field(default_factory=tuple)
    explanation: str = ""
    evidence_relationship_ids: tuple[str, ...] = field(default_factory=tuple)

    def __init__(
        self,
        matched: bool,
        confidence: str = "LOW",
        signals: Iterable[str] = (),
        evidence_fact_ids: Iterable[str] = (),
        evidence_edge_ids: Iterable[str] = (),
        explanation: str = "",
        evidence_relationship_ids: Iterable[str] = (),
    ):
        object.__setattr__(self, 'matched', matched)
        object.__setattr__(self, 'confidence', confidence)
        object.__setattr__(self, 'signals', tuple(sorted(set(signals))))
        object.__setattr__(self, 'evidence_fact_ids', tuple(sorted(set(evidence_fact_ids))))
        object.__setattr__(self, 'evidence_edge_ids', tuple(sorted(set(evidence_edge_ids))))
        object.__setattr__(self, 'explanation', explanation)
        object.__setattr__(self, 'evidence_relationship_ids', tuple(sorted(set(evidence_relationship_ids))))

        # Backward compatibility for existing callers expecting relationship IDs only
        if not object.__getattribute__(self, 'evidence_relationship_ids') and evidence_edge_ids:
            object.__setattr__(self, 'evidence_relationship_ids', tuple(sorted(set(evidence_edge_ids))))

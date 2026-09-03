from abc import ABC, abstractmethod
from dataclasses import dataclass

from src.analysis.predicates.engine import PredicateEngine
from src.graph.models import ResolvedRelationship
from src.resolution.registry import GlobalSymbolRegistry

from .models import Finding


@dataclass(frozen=True)
class DetectionContext:
    predicates: PredicateEngine
    registry: GlobalSymbolRegistry
    valid_relationship_ids: frozenset[str]
    # Approved read-only access to Layer 2 provenance for confidence derivation.
    # Detectors must NOT use this to traverse AST or perform symbol resolution.
    relationships: tuple  # tuple[ResolvedRelationship, ...]

    def get_relationship(self, rel_id: str) -> "ResolvedRelationship | None":
        """Look up a resolved relationship by ID from the approved context."""
        for rel in self.relationships:
            if rel.relationship_id == rel_id:
                return rel
        return None

class BaseDetector(ABC):
    detector_id: str
    pattern_name: str
    category: str

    @abstractmethod
    def detect(self, context: DetectionContext) -> list[Finding]:
        """
        Execute detection logic using semantic predicates.
        Must NOT parse AST, traverse raw facts, or build graph projections.
        """

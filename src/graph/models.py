from __future__ import annotations

import hashlib
import uuid
from dataclasses import dataclass, field
from enum import Enum


class EdgeType(str, Enum):
    # Legacy edges (kept for backward compatibility with graph analytics)
    IMPORTS      = "IMPORTS"
    CONTAINS     = "CONTAINS"
    USES_API     = "USES_API"      # Legacy: will be superseded by CALLS/INSTANTIATES
    # Canonical Layer-2 semantic edges
    CALLS        = "CALLS"
    INSTANTIATES = "INSTANTIATES"
    INHERITS     = "INHERITS"
    COMPOSES     = "COMPOSES"


@dataclass
class TypedEdge:
    source_id: str
    target_id: str
    edge_type: EdgeType
    evidence_fact_ids: list[str]
    edge_id: str = field(default_factory=lambda: str(uuid.uuid4()))


@dataclass
class ResolvedEdge:
    """
    Canonical contract between the resolution layer and graph layer.

    This is the standard representation for a resolved semantic edge regardless
    of whether the legacy Layer-2 model is still named ResolvedRelationship.
    """
    source_id: str
    target_id: str
    relationship: str
    confidence: float = 1.0
    evidence_fact_ids: list[str] = field(default_factory=list)
    resolution_status: str = "UNRESOLVED"
    resolution_domain: str = "UNRESOLVED"
    resolution_method: str = ""
    edge_id: str = field(default_factory=lambda: str(uuid.uuid4()))

    def __post_init__(self):
        if self.relationship and not isinstance(self.relationship, str):
            self.relationship = self.relationship.value


def _deterministic_rel_id(relationship_type: str, source_fqn: str, target_fqn: str) -> str:
    """
    Produce a deterministic SHA-256 relationship ID.

    Hashes (relationship_type_value, source_fqn, target_fqn).
    evidence_fact_ids are NOT included: fact_ids use uuid4() and are
    non-deterministic across parallel vs single-process runs.
    The semantic identity of a relationship is fully captured by the triple.
    """
    key = f"{relationship_type}|{source_fqn}|{target_fqn}"
    return hashlib.sha256(key.encode()).hexdigest()


@dataclass
class ResolvedRelationship:
    """
    Intermediate Layer-2 model carrying full resolution provenance.

    Every derived semantic graph edge (CALLS, INSTANTIATES, INHERITS, COMPOSES)
    originates here and must be traceable back to its raw Layer-1 fact IDs.

    Contractual rule: the resolver never guesses — unresolved/ambiguous evidence
    is preserved here and excluded from the typed graph, not discarded.

    relationship_id is deterministic: it is a hash of
    (relationship_type, source_fqn, target_fqn, sorted evidence_fact_ids)
    so parallel and sequential runs produce identical IDs for the same relationship.
    """
    relationship_type: EdgeType
    source_fqn: str                    # e.g. "services.user.UserService.save"
    target_fqn: str                    # e.g. "db.repo.UserRepository"
    resolution_status: str             # ResolutionStatus value
    resolution_domain: str             # ResolutionDomain value
    confidence: str                    # Confidence value
    resolution_method: str             # ResolutionMethod value — for debuggability
    evidence_fact_ids: list[str]       # raw fact IDs (CallFact, InheritanceFact, etc.)
    relationship_id: str = field(default="")

    def __post_init__(self):
        if not self.relationship_id:
            # Use .value to get "CALLS" not "EdgeType.CALLS" — Python's str,Enum
            # str() returns the qualified name ("EdgeType.CALLS") not the value.
            type_val = (
                self.relationship_type.value
                if hasattr(self.relationship_type, "value")
                else str(self.relationship_type)
            )
            self.relationship_id = _deterministic_rel_id(
                type_val, self.source_fqn, self.target_fqn
            )

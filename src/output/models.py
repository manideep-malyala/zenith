from dataclasses import dataclass
from typing import Any


@dataclass
class SourceLocation:
    file: str
    line: int

    def to_dict(self) -> dict[str, Any]:
        return {"file": self.file, "line": self.line}


@dataclass
class Finding:
    finding_id: str
    capability_id: str
    category: str
    status: str
    confidence: float
    evidence_refs: list[str]
    source_locations: list[SourceLocation]
    graph_score: float = 0.0
    educational_value: float = 0.0
    explanation: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "finding_id": self.finding_id,
            "capability_id": self.capability_id,
            "category": self.category,
            "status": self.status,
            "confidence": self.confidence,
            "evidence_refs": self.evidence_refs,
            "source_locations": [loc.to_dict() for loc in self.source_locations],
            "graph_score": self.graph_score,
            "educational_value": self.educational_value,
            "explanation": self.explanation,
        }


@dataclass
class AnalysisResult:
    metadata: dict
    files: dict
    facts: dict[str, Any]
    relationships: dict[str, Any]
    capabilities: dict[str, Any]
    findings: list[Finding]
    graph_metrics: dict[str, Any]

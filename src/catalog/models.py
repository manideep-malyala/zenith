from dataclasses import dataclass, field
from typing import Any

from .capabilities import Answerability


@dataclass
class EvidenceItem:
    file: str
    line: int
    fact_type: str
    symbol: str

@dataclass
class EvidencePackage:
    question: str
    concept: str
    operation: str
    answerability: Answerability
    confidence: float
    summary: dict[str, Any] = field(default_factory=dict)
    evidence: list[EvidenceItem] = field(default_factory=list)
    signals: list[str] = field(default_factory=list)
    limitations: list[str] = field(default_factory=list)
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "question": self.question,
            "concept": self.concept,
            "operation": self.operation,
            "answerability": self.answerability.value,
            "confidence": self.confidence,
            "summary": self.summary,
            "evidence": [
                {
                    "file": e.file,
                    "line": e.line,
                    "fact_type": e.fact_type,
                    "symbol": e.symbol
                } for e in self.evidence
            ],
            "signals": self.signals,
            "limitations": self.limitations
        }

from dataclasses import dataclass
from enum import Enum


class Answerability(str, Enum):
    DIRECT = "DIRECT"
    HEURISTIC = "HEURISTIC"
    UNANSWERABLE = "UNANSWERABLE"

class Operation(str, Enum):
    LOCATE = "LOCATE"
    COUNT = "COUNT"
    SUMMARIZE = "SUMMARIZE"
    COMPARE = "COMPARE"
    DETECT = "DETECT"
    EXPLAIN = "EXPLAIN"
    TRACE = "TRACE"

@dataclass
class Capability:
    concept: str
    operations: list[Operation]
    resolver_path: str
    answerability: Answerability
    description: str = ""
    learning_candidate: bool = False
    educational_value: float = 0.5

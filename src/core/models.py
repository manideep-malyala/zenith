import time
import uuid
from dataclasses import dataclass, field
from enum import Enum

from .context import ASTContext
from .profiler import profiler


def generate_fact_id() -> str:
    t0 = time.time()
    val = str(uuid.uuid4())
    profiler.stats["fact_id_generation_seconds"] += (time.time() - t0)
    return val

class ResolutionStatus(str, Enum):
    """How confidently a symbolic target was resolved."""
    RESOLVED   = "RESOLVED"    # Exact, unique match
    PARTIAL    = "PARTIAL"     # Namespace known, but exact definition unavailable (e.g. external)
    UNRESOLVED = "UNRESOLVED"  # Could not determine meaningful target
    AMBIGUOUS  = "AMBIGUOUS"   # Multiple plausible local candidates

class ResolutionDomain(str, Enum):
    """Where the resolved target lives."""
    LOCAL      = "LOCAL"       # Defined inside this project
    EXTERNAL   = "EXTERNAL"    # Third-party / stdlib module
    BUILTIN    = "BUILTIN"     # Python built-in (builtins.*)
    UNRESOLVED = "UNRESOLVED"  # Domain could not be determined
    AMBIGUOUS  = "AMBIGUOUS"   # Multiple candidates across domains

class Confidence(str, Enum):
    """How much the resolver trusts this relationship."""
    HIGH   = "HIGH"    # Single unambiguous match via explicit import or same-file lookup
    MEDIUM = "MEDIUM"  # Heuristic or partial match (e.g. namespace-only, typed annotation)
    LOW    = "LOW"     # Naming-convention guess only

class ResolutionMethod(str, Enum):
    """Which resolution path was used — for traceability."""
    EXPLICIT_IMPORT  = "EXPLICIT_IMPORT"   # Resolved via a direct import in-scope
    ALIAS_IMPORT     = "ALIAS_IMPORT"      # Resolved via 'import X as Y'
    SAME_FILE        = "SAME_FILE"         # Resolved to a definition in the same file
    GLOBAL_FQN       = "GLOBAL_FQN"        # Resolved via fully-qualified name in global registry
    BARE_NAME        = "BARE_NAME"         # Bare-name fallback (lowest priority)
    BUILTIN          = "BUILTIN"           # Matched against builtins.*
    EXTERNAL_SYMBOL  = "EXTERNAL_SYMBOL"   # Resolved to an external/third-party namespace

@dataclass
class ImportFact:
    file_path: str
    line: int
    module: str
    symbol: str | None
    alias: str | None
    fact_id: str = field(default_factory=generate_fact_id)
    context: ASTContext | None = None

@dataclass
class DefinitionFact:
    definition_type: str  # e.g. 'function', 'method', 'class'
    name: str
    qualified_name: str
    file_path: str
    start_line: int
    end_line: int
    is_async: bool = False
    has_return_annotation: bool = False
    has_param_annotation: bool = False
    fact_id: str = field(default_factory=generate_fact_id)
    context: ASTContext | None = None

@dataclass
class CallFact:
    file_path: str
    line: int
    func_name: str
    receiver: str | None
    fact_id: str = field(default_factory=generate_fact_id)
    resolved_symbol: str | None = None
    resolution_status: ResolutionStatus = ResolutionStatus.UNRESOLVED
    context: ASTContext | None = None

@dataclass
class TryFact:
    file_path: str
    line: int
    handlers: int
    has_else: bool
    has_finally: bool
    is_star: bool = False
    caught_exceptions: list[str] = field(default_factory=list)
    fact_id: str = field(default_factory=generate_fact_id)
    context: ASTContext | None = None

@dataclass
class RaiseFact:
    file_path: str
    line: int
    exception_expression: str | None
    cause: str | None
    fact_id: str = field(default_factory=generate_fact_id)
    context: ASTContext | None = None

@dataclass
class LambdaFact:
    file_path: str
    line: int
    parameters: list[str]
    defaults_count: int
    fact_id: str = field(default_factory=generate_fact_id)
    context: ASTContext | None = None

@dataclass
class DecoratorFact:
    file_path: str
    line: int
    target_name: str
    target_type: str # 'function', 'class', 'method'
    decorator_expression: str
    resolved_symbol: str | None = None
    fact_id: str = field(default_factory=generate_fact_id)
    context: ASTContext | None = None

@dataclass
class AsyncFact:
    file_path: str
    line: int
    kind: str # 'await', 'async_for', 'async_with'
    fact_id: str = field(default_factory=generate_fact_id)
    context: ASTContext | None = None

@dataclass
class WithFact:
    file_path: str
    line: int
    is_async: bool
    items_count: int
    fact_id: str = field(default_factory=generate_fact_id)
    context: ASTContext | None = None

@dataclass
class LoopFact:
    file_path: str
    line: int
    kind: str # 'for', 'async_for', 'while'
    has_break: bool
    has_continue: bool
    has_else: bool
    fact_id: str = field(default_factory=generate_fact_id)
    context: ASTContext | None = None

@dataclass
class ConditionalFact:
    file_path: str
    line: int
    kind: str # 'if', 'match'
    branch_count: int
    fact_id: str = field(default_factory=generate_fact_id)
    context: ASTContext | None = None

@dataclass
class ComprehensionFact:
    file_path: str
    line: int
    kind: str # 'list', 'set', 'dict', 'generator'
    generators_count: int
    filter_count: int
    fact_id: str = field(default_factory=generate_fact_id)
    context: ASTContext | None = None

@dataclass
class GeneratorFact:
    file_path: str
    line: int
    kind: str # 'yield', 'yield_from'
    fact_id: str = field(default_factory=generate_fact_id)
    context: ASTContext | None = None

@dataclass
class AssignmentFact:
    file_path: str
    line: int
    kind: str            # 'assign', 'ann_assign', 'aug_assign', 'named_expr'
    target_kind: str     # 'NAME', 'ATTRIBUTE', 'SUBSCRIPT', 'TUPLE_UNPACK', 'OTHER'
    target_name: str | None
    has_annotation: bool
    # Enrichment for COMPOSES resolution: captured at extraction time to avoid re-parsing.
    # rhs_expression: textual RHS (e.g. 'Repository()', 'repo', '0', '"test"').
    # annotation_expression: type annotation text if present (e.g. 'Repository', 'Optional[str]').
    rhs_expression: str | None = None
    annotation_expression: str | None = None
    fact_id: str = field(default_factory=generate_fact_id)
    context: ASTContext | None = None

@dataclass
class InheritanceFact:
    file_path: str
    line: int
    class_name: str
    base_expression: str # e.g. 'Base', 'pkg.Base', 'Generic[T]'
    fact_id: str = field(default_factory=generate_fact_id)
    context: ASTContext | None = None

@dataclass
class ReturnFact:
    file_path: str
    line: int
    has_value: bool
    fact_id: str = field(default_factory=generate_fact_id)
    context: ASTContext | None = None

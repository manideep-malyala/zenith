"""
RelationshipResolver — Layer 2, Pass 3.

Consumes raw Layer-1 facts and the per-file ScopeResolvers to emit
ResolvedRelationship objects with full provenance:

  CallFact        → CALLS | INSTANTIATES
  InheritanceFact → INHERITS
  AssignmentFact  → COMPOSES  (strictly guarded — see rules below)

Contractual rule:
  The resolver NEVER guesses. Unresolved / ambiguous relationships are
  preserved in the output with appropriate status/domain, but are NOT
  added to the typed graph. Every emitted relationship is traceable back
  to one or more raw fact IDs.

Resolution priority (per the approved design):
  1. Explicit import / alias match in file scope
  2. Qualified module path match (receiver.attr)
  3. Same-file / lexical scope (registry lookup by file + bare name)
  4. Global exact FQN match
  5. Bare-name fallback (only if single unambiguous candidate)
  6. AMBIGUOUS if >1 local candidate remains

COMPOSES rules (strict):
  - Only self-attribute assignments: target_kind == 'ATTRIBUTE' and target_name
    refers to a self-attribute (we detect this from context.enclosing_class).
  - RHS must resolve to a meaningful symbol via ONE of:
      a) Direct instantiation: rhs_expression ends with '()' and the base name
         resolves to a LOCAL class in the registry.   → HIGH confidence
      b) Typed parameter:      annotation_expression resolves to a LOCAL class.
         → HIGH confidence (type annotation is explicit evidence)
      c) Untyped parameter:    NO COMPOSES emitted. Do not guess.
  - Primitive-literal RHS (int, float, str, bool, None, bytes) is always excluded.
"""

import builtins
import re

from src.core.models import (
    AssignmentFact,
    CallFact,
    Confidence,
    InheritanceFact,
    ResolutionDomain,
    ResolutionMethod,
    ResolutionStatus,
)
from src.graph.models import EdgeType, ResolvedRelationship
from src.resolution.registry import GlobalSymbolRegistry
from src.resolution.symbol_resolver import ScopeResolver

_BUILTIN_NAMES = frozenset(dir(builtins))

# Patterns that identify a primitive literal — these never constitute composition targets.
_PRIMITIVE_LITERAL_RE = re.compile(
    r"""^(
        -?\d+(\.\d+)?           |   # int / float
        True|False|None         |   # bool / None
        b?["']                  |   # str / bytes literal
        \[.*\]|\{.*\}|\(.*,.*\)    # list / dict / tuple literal (simple)
    )""",
    re.VERBOSE,
)


def _is_primitive(expr: str | None) -> bool:
    if expr is None:
        return True
    return bool(_PRIMITIVE_LITERAL_RE.match(expr.strip()))


def _call_base_name(rhs: str) -> str | None:
    """
    Extract the callable name from a call expression.
    'Repository()'        -> 'Repository'
    'repo.Repository()'   -> 'Repository'  (last segment)
    'create_repo()'       -> 'create_repo'
    Returns None if rhs doesn't look like a call.
    """
    stripped = rhs.strip()
    if "(" not in stripped or not stripped.endswith(")"):
        return None
    base = stripped[: stripped.index("(")].strip()
    return base.split(".")[-1] if base else None


class RelationshipResolver:
    """
    Resolves raw facts → ResolvedRelationship objects (Layer 2, Pass 3).
    """

    def __init__(
        self,
        registry: GlobalSymbolRegistry,
        scope_resolvers: dict[str, ScopeResolver],
    ):
        self._registry = registry
        self._scopes = scope_resolvers  # file_path → ScopeResolver

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------

    def resolve_all(
        self,
        calls: list[CallFact],
        inheritances: list[InheritanceFact],
        assignments: list[AssignmentFact],
    ) -> list[ResolvedRelationship]:
        results: list[ResolvedRelationship] = []
        results.extend(self._resolve_calls(calls))
        results.extend(self._resolve_inheritances(inheritances))
        results.extend(self._resolve_composes(assignments))
        return results

    # ------------------------------------------------------------------
    # Source FQN helper
    # ------------------------------------------------------------------

    def _source_fqn(self, file_path: str, context) -> str:
        """
        Build a FQN for the enclosing callable/class from Layer-1 context.
        Falls back to the module FQN if no enclosing scope is available.
        """
        module = self._registry._file_to_module(file_path) or file_path
        if context is None:
            return module
        parts = [module]
        if context.enclosing_class:
            parts.append(context.enclosing_class)
        if context.enclosing_function:
            parts.append(context.enclosing_function)
        return ".".join(parts)

    # ------------------------------------------------------------------
    # Pass 3a — CallFact → CALLS / INSTANTIATES
    # ------------------------------------------------------------------

    def _resolve_calls(self, calls: list[CallFact]) -> list[ResolvedRelationship]:
        results = []
        for call in calls:
            rel = self._resolve_single_call(call)
            if rel:
                results.append(rel)
        return results

    def _resolve_single_call(self, call: CallFact) -> ResolvedRelationship | None:
        scope = self._scopes.get(call.file_path)
        source_fqn = self._source_fqn(call.file_path, call.context)

        # --- Priority 1 & 2: receiver.attr or bare name via scope ---
        entry = None
        if call.receiver:
            entry = scope.resolve_receiver_attr(call.receiver, call.func_name) if scope else None
        if entry is None:
            entry = scope.resolve(call.func_name) if scope else None

        # --- Priority 3: same-file lookup ---
        if entry is None:
            same_file_defs = [
                d for d in self._registry.lookup_name(call.func_name)
                if d.file_path == call.file_path
            ]
            if len(same_file_defs) == 1:
                defn = same_file_defs[0]
                target_fqn = self._registry._to_fqn(defn)
                return self._make_call_rel(
                    call, source_fqn, target_fqn,
                    ResolutionStatus.RESOLVED, ResolutionDomain.LOCAL,
                    Confidence.HIGH, ResolutionMethod.SAME_FILE, defn,
                )

        # --- Priority 4: global exact FQN (qualified call like 'pkg.mod.Foo()') ---
        if entry is None and call.receiver:
            qualified = f"{call.receiver}.{call.func_name}"
            defn = self._registry.lookup(qualified)
            if defn:
                target_fqn = self._registry._to_fqn(defn)
                return self._make_call_rel(
                    call, source_fqn, target_fqn,
                    ResolutionStatus.RESOLVED, ResolutionDomain.LOCAL,
                    Confidence.HIGH, ResolutionMethod.GLOBAL_FQN, defn,
                )

        # --- Priority 5: bare-name fallback (only if unambiguous) ---
        if entry is None:
            candidates = self._registry.lookup_name(call.func_name)
            if len(candidates) == 1:
                defn = candidates[0]
                target_fqn = self._registry._to_fqn(defn)
                return self._make_call_rel(
                    call, source_fqn, target_fqn,
                    ResolutionStatus.RESOLVED, ResolutionDomain.LOCAL,
                    Confidence.MEDIUM, ResolutionMethod.BARE_NAME, defn,
                )
            elif len(candidates) > 1:
                # AMBIGUOUS — multiple local candidates
                return ResolvedRelationship(
                    relationship_type=EdgeType.CALLS,
                    source_fqn=source_fqn,
                    target_fqn=call.func_name,
                    resolution_status=ResolutionStatus.AMBIGUOUS.value,
                    resolution_domain=ResolutionDomain.AMBIGUOUS.value,
                    confidence=Confidence.LOW.value,
                    resolution_method=ResolutionMethod.BARE_NAME.value,
                    evidence_fact_ids=[call.fact_id],
                )

        # --- Scope entry found ---
        if entry:
            if entry.domain == ResolutionDomain.AMBIGUOUS or not entry.fqn:
                return ResolvedRelationship(
                    relationship_type=EdgeType.CALLS,
                    source_fqn=source_fqn,
                    target_fqn=call.func_name,
                    resolution_status=ResolutionStatus.AMBIGUOUS.value,
                    resolution_domain=ResolutionDomain.AMBIGUOUS.value,
                    confidence=Confidence.LOW.value,
                    resolution_method=ResolutionMethod.BARE_NAME.value,
                    evidence_fact_ids=[call.fact_id],
                )
            defn = self._registry.lookup(entry.fqn)
            return self._make_call_rel(
                call, source_fqn, entry.fqn,
                ResolutionStatus.RESOLVED if defn else ResolutionStatus.PARTIAL,
                entry.domain,
                Confidence.HIGH if defn else Confidence.MEDIUM,
                entry.method, defn,
            )

        # --- Builtin fallback ---
        if call.func_name in _BUILTIN_NAMES:
            return ResolvedRelationship(
                relationship_type=EdgeType.CALLS,
                source_fqn=source_fqn,
                target_fqn=f"builtins.{call.func_name}",
                resolution_status=ResolutionStatus.RESOLVED.value,
                resolution_domain=ResolutionDomain.BUILTIN.value,
                confidence=Confidence.HIGH.value,
                resolution_method=ResolutionMethod.BUILTIN.value,
                evidence_fact_ids=[call.fact_id],
            )

        # --- Truly unresolved ---
        return ResolvedRelationship(
            relationship_type=EdgeType.CALLS,
            source_fqn=source_fqn,
            target_fqn=call.func_name,
            resolution_status=ResolutionStatus.UNRESOLVED.value,
            resolution_domain=ResolutionDomain.UNRESOLVED.value,
            confidence=Confidence.LOW.value,
            resolution_method=ResolutionMethod.BARE_NAME.value,
            evidence_fact_ids=[call.fact_id],
        )

    def _looks_like_class_name(self, target_fqn: str) -> bool:
        if not target_fqn:
            return False
        name = target_fqn.split(".")[-1]
        return bool(name) and name[:1].isupper()

    def _make_call_rel(
        self, call, source_fqn, target_fqn,
        status, domain, confidence, method, defn
    ) -> ResolvedRelationship:
        """Select CALLS vs INSTANTIATES based on the resolved definition type."""
        edge_type = EdgeType.CALLS
        if defn and defn.definition_type == "class" or self._looks_like_class_name(target_fqn):
            edge_type = EdgeType.INSTANTIATES
        return ResolvedRelationship(
            relationship_type=edge_type,
            source_fqn=source_fqn,
            target_fqn=target_fqn,
            resolution_status=status.value,
            resolution_domain=domain.value,
            confidence=confidence.value,
            resolution_method=method.value,
            evidence_fact_ids=[call.fact_id],
        )

    # ------------------------------------------------------------------
    # Pass 3b — InheritanceFact → INHERITS
    # ------------------------------------------------------------------

    def _resolve_inheritances(
        self, inheritances: list[InheritanceFact]
    ) -> list[ResolvedRelationship]:
        results = []
        for inh in inheritances:
            rel = self._resolve_single_inheritance(inh)
            if rel:
                results.append(rel)
        return results

    def _resolve_single_inheritance(
        self, inh: InheritanceFact
    ) -> ResolvedRelationship | None:
        scope = self._scopes.get(inh.file_path)
        module = self._registry._file_to_module(inh.file_path) or inh.file_path
        source_fqn = f"{module}.{inh.class_name}" if module else inh.class_name

        # Strip subscripts: 'Generic[T]' → 'Generic', 'Optional[str]' → 'Optional'
        raw_base = inh.base_expression.split("[")[0].strip()
        # Strip leading dots (relative imports like '.Base')
        raw_base = raw_base.lstrip(".")

        # Priority 1/2: scope lookup
        entry = scope.resolve(raw_base) if scope else None
        if entry:
            defn = self._registry.lookup(entry.fqn)
            return ResolvedRelationship(
                relationship_type=EdgeType.INHERITS,
                source_fqn=source_fqn,
                target_fqn=entry.fqn,
                resolution_status=(ResolutionStatus.RESOLVED if defn else ResolutionStatus.PARTIAL).value,
                resolution_domain=entry.domain.value,
                confidence=(Confidence.HIGH if defn else Confidence.MEDIUM).value,
                resolution_method=entry.method.value,
                evidence_fact_ids=[inh.fact_id],
            )

        # Priority 3: same-file
        same_file = [
            d for d in self._registry.lookup_name(raw_base)
            if d.file_path == inh.file_path and d.definition_type == "class"
        ]
        if len(same_file) == 1:
            defn = same_file[0]
            return ResolvedRelationship(
                relationship_type=EdgeType.INHERITS,
                source_fqn=source_fqn,
                target_fqn=self._registry._to_fqn(defn),
                resolution_status=ResolutionStatus.RESOLVED.value,
                resolution_domain=ResolutionDomain.LOCAL.value,
                confidence=Confidence.HIGH.value,
                resolution_method=ResolutionMethod.SAME_FILE.value,
                evidence_fact_ids=[inh.fact_id],
            )

        # Priority 4/5: global bare-name
        candidates = self._registry.lookup_name(raw_base)
        class_candidates = [d for d in candidates if d.definition_type == "class"]
        if len(class_candidates) == 1:
            defn = class_candidates[0]
            return ResolvedRelationship(
                relationship_type=EdgeType.INHERITS,
                source_fqn=source_fqn,
                target_fqn=self._registry._to_fqn(defn),
                resolution_status=ResolutionStatus.RESOLVED.value,
                resolution_domain=ResolutionDomain.LOCAL.value,
                confidence=Confidence.MEDIUM.value,
                resolution_method=ResolutionMethod.BARE_NAME.value,
                evidence_fact_ids=[inh.fact_id],
            )
        if len(class_candidates) > 1:
            return ResolvedRelationship(
                relationship_type=EdgeType.INHERITS,
                source_fqn=source_fqn,
                target_fqn=raw_base,
                resolution_status=ResolutionStatus.AMBIGUOUS.value,
                resolution_domain=ResolutionDomain.AMBIGUOUS.value,
                confidence=Confidence.LOW.value,
                resolution_method=ResolutionMethod.BARE_NAME.value,
                evidence_fact_ids=[inh.fact_id],
            )

        # Could be external (e.g. 'ABC', 'Generic')
        return ResolvedRelationship(
            relationship_type=EdgeType.INHERITS,
            source_fqn=source_fqn,
            target_fqn=raw_base,
            resolution_status=ResolutionStatus.PARTIAL.value,
            resolution_domain=ResolutionDomain.EXTERNAL.value,
            confidence=Confidence.MEDIUM.value,
            resolution_method=ResolutionMethod.EXTERNAL_SYMBOL.value,
            evidence_fact_ids=[inh.fact_id],
        )

    # ------------------------------------------------------------------
    # Pass 3c — AssignmentFact → COMPOSES (strictly guarded)
    # ------------------------------------------------------------------

    def _resolve_composes(
        self, assignments: list[AssignmentFact]
    ) -> list[ResolvedRelationship]:
        results = []
        for asgn in assignments:
            rel = self._resolve_single_compose(asgn)
            if rel:
                results.append(rel)
        return results

    def _resolve_single_compose(
        self, asgn: AssignmentFact
    ) -> ResolvedRelationship | None:
        # Gate 1: must be a self-attribute assignment
        if asgn.target_kind != "ATTRIBUTE":
            return None
        # Require enclosing class (self-attribute pattern)
        ctx = asgn.context
        if not ctx or not ctx.enclosing_class:
            return None

        scope = self._scopes.get(asgn.file_path)
        module = self._registry._file_to_module(asgn.file_path) or asgn.file_path
        source_fqn = f"{module}.{ctx.enclosing_class}"

        # Gate 2a: Direct instantiation — rhs_expression ends with '()'
        if asgn.rhs_expression and not _is_primitive(asgn.rhs_expression):
            base_name = _call_base_name(asgn.rhs_expression)
            if base_name:
                resolved = self._resolve_class_name(base_name, asgn.file_path, scope)
                if resolved:
                    target_fqn, domain, method, _defn = resolved
                    return ResolvedRelationship(
                        relationship_type=EdgeType.COMPOSES,
                        source_fqn=source_fqn,
                        target_fqn=target_fqn,
                        resolution_status=ResolutionStatus.RESOLVED.value,
                        resolution_domain=domain.value,
                        confidence=Confidence.HIGH.value,
                        resolution_method=method.value,
                        evidence_fact_ids=[asgn.fact_id],
                    )

        # Gate 2b: Typed parameter — annotation_expression resolves to a local class
        if asgn.annotation_expression and not _is_primitive(asgn.annotation_expression):
            ann_base = asgn.annotation_expression.split("[")[0].strip()
            resolved = self._resolve_class_name(ann_base, asgn.file_path, scope)
            if resolved:
                target_fqn, domain, method, _defn = resolved
                return ResolvedRelationship(
                    relationship_type=EdgeType.COMPOSES,
                    source_fqn=source_fqn,
                    target_fqn=target_fqn,
                    resolution_status=ResolutionStatus.RESOLVED.value,
                    resolution_domain=domain.value,
                    confidence=Confidence.HIGH.value,
                    resolution_method=method.value,
                    evidence_fact_ids=[asgn.fact_id],
                )

        # Gate 2c: untyped parameter — do not emit COMPOSES
        return None

    def _resolve_class_name(self, name: str, file_path: str, scope: ScopeResolver | None):
        """
        Try to resolve 'name' to a class definition.
        Returns (target_fqn, domain, method, defn) or None.
        """
        # Scope lookup first
        if scope:
            entry = scope.resolve(name)
            if entry:
                defn = self._registry.lookup(entry.fqn)
                if defn and defn.definition_type == "class":
                    return (entry.fqn, entry.domain, entry.method, defn)
                if defn is None and entry.domain == ResolutionDomain.LOCAL:
                    # Partially resolved local
                    return (entry.fqn, entry.domain, entry.method, None)

        # Same-file fallback
        same_file = [
            d for d in self._registry.lookup_name(name)
            if d.file_path == file_path and d.definition_type == "class"
        ]
        if len(same_file) == 1:
            defn = same_file[0]
            return (
                self._registry._to_fqn(defn),
                ResolutionDomain.LOCAL,
                ResolutionMethod.SAME_FILE,
                defn,
            )

        # Global bare-name (only if unambiguous class)
        candidates = [
            d for d in self._registry.lookup_name(name)
            if d.definition_type == "class"
        ]
        if len(candidates) == 1:
            defn = candidates[0]
            return (
                self._registry._to_fqn(defn),
                ResolutionDomain.LOCAL,
                ResolutionMethod.BARE_NAME,
                defn,
            )

        return None

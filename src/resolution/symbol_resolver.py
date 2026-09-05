"""
ScopeResolver — Layer 2, Pass 2.

Builds a per-file scope table from a file's ImportFacts and the GlobalSymbolRegistry.
Maps every locally-visible name to a fully-qualified name and a resolution domain.

Resolution priority (highest → lowest):
  1. Explicit import:     from services.user import UserService
  2. Alias import:        from services.user import UserService as Service
  3. Module import alias: import services.user as m
  4. Plain module import: import services.user
  (Same-file and bare-name lookups are handled in RelationshipResolver using the registry.)

Domain classification:
  LOCAL    — FQN is a known local module or definition.
  EXTERNAL — FQN is not in the local registry and not a builtin.
  BUILTIN  — Matches Python builtins.
"""

import builtins
import os

from src.core.models import (
    CallFact,
    ImportFact,
    ResolutionDomain,
    ResolutionMethod,
    ResolutionStatus,
)
from src.resolution.registry import GlobalSymbolRegistry

_BUILTIN_NAMES = frozenset(dir(builtins))


class _ScopeEntry:
    __slots__ = ("domain", "fqn", "method")

    def __init__(self, fqn: str, domain: ResolutionDomain, method: ResolutionMethod):
        self.fqn = fqn
        self.domain = domain
        self.method = method


class ScopeResolver:
    """
    Per-file name → (fqn, domain, method) table.

    Usage:
        scope = ScopeResolver(file_imports, registry, file_path)
        result = scope.resolve("UserService")  # → _ScopeEntry or None
    """

    def __init__(
        self,
        imports: list[ImportFact],
        registry: GlobalSymbolRegistry,
        file_path: str,
    ):
        self._registry = registry
        self._file_path = file_path
        # name → _ScopeEntry
        self._scope: dict[str, _ScopeEntry] = {}
        self._build(imports)

    # ------------------------------------------------------------------
    # Build
    # ------------------------------------------------------------------

    def _build(self, imports: list[ImportFact]) -> None:
        for imp in imports:
            if imp.symbol:
                # from module import symbol [as alias]
                local_name = imp.alias if imp.alias else imp.symbol
                fqn = f"{imp.module}.{imp.symbol}" if imp.module else imp.symbol
                method = ResolutionMethod.ALIAS_IMPORT if imp.alias else ResolutionMethod.EXPLICIT_IMPORT
                domain = self._classify_fqn(fqn)
                if local_name in self._scope:
                    self._scope[local_name] = _ScopeEntry("", ResolutionDomain.AMBIGUOUS, method)
                else:
                    self._scope[local_name] = _ScopeEntry(fqn, domain, method)
            else:
                # import module [as alias]
                local_name = imp.alias if imp.alias else imp.module
                fqn = imp.module
                method = ResolutionMethod.ALIAS_IMPORT if imp.alias else ResolutionMethod.EXPLICIT_IMPORT
                domain = self._classify_fqn(fqn)
                if local_name in self._scope:
                    self._scope[local_name] = _ScopeEntry("", ResolutionDomain.AMBIGUOUS, method)
                else:
                    self._scope[local_name] = _ScopeEntry(fqn, domain, method)

    def _classify_fqn(self, fqn: str) -> ResolutionDomain:
        """Classify a fqn as LOCAL, EXTERNAL, or BUILTIN."""
        if not fqn:
            return ResolutionDomain.EXTERNAL
        root = fqn.split(".")[0]
        if self._registry.is_local_fqn(fqn) or self._registry.is_local_module(fqn):
            return ResolutionDomain.LOCAL
        if self._registry.is_local_module(root):
            # The root is local but this exact symbol wasn't indexed (e.g. a sub-module)
            return ResolutionDomain.LOCAL
        if root in _BUILTIN_NAMES:
            return ResolutionDomain.BUILTIN
        return ResolutionDomain.EXTERNAL

    # ------------------------------------------------------------------
    # Resolution API
    # ------------------------------------------------------------------

    def resolve(self, name: str) -> _ScopeEntry | None:
        """
        Resolve a bare name to a scope entry.
        Returns None if the name is not visible in this file's import scope.
        """
        return self._scope.get(name)

    def resolve_receiver_attr(self, receiver: str, attr: str) -> _ScopeEntry | None:
        """
        Resolve 'receiver.attr' style calls.

        Handles both imported modules (e.g. 'concurrent.futures' + 'ThreadPoolExecutor')
        and aliased names (e.g. 'module_alias' + 'Method'). If the receiver itself is
        dotted, we attempt each prefix in order so 'pkg.subpkg' can resolve cleanly.
        """
        if not receiver:
            return None

        candidates = [receiver]
        if "." in receiver:
            parts = receiver.split(".")
            candidates.extend(".".join(parts[:i]) for i in range(1, len(parts)))

        for candidate in candidates:
            entry = self._scope.get(candidate)
            if entry is None:
                continue
            fqn = f"{entry.fqn}.{attr}"
            domain = self._classify_fqn(fqn)
            return _ScopeEntry(fqn, domain, entry.method)

        return None

    def file_path(self) -> str:
        return self._file_path


class SymbolResolver:
    """
    Compatibility shim for older callers/tests that still expect a single
    SymbolResolver API with resolve_call(). It delegates to the modern
    ScopeResolver + GlobalSymbolRegistry pipeline.
    """

    def __init__(self, imports: list[ImportFact], project_root: str = ".", file_path: str | None = None):
        self.imports = list(imports or [])
        self.project_root = os.path.abspath(project_root)
        self.file_path = file_path or "<memory>"
        self.registry = GlobalSymbolRegistry(self.project_root)
        self.scope = ScopeResolver(self.imports, self.registry, self.file_path)

    def resolve_call(self, call: CallFact) -> str | None:
        if call.receiver:
            entry = self.scope.resolve_receiver_attr(call.receiver, call.func_name)
        else:
            entry = self.scope.resolve(call.func_name)

        if entry is not None:
            resolved = entry.fqn
            call.resolved_symbol = resolved
            call.resolution_status = ResolutionStatus.RESOLVED
            return resolved

        same_file_defs = [
            d for d in self.registry.lookup_name(call.func_name)
            if d.file_path == call.file_path
        ]
        if len(same_file_defs) == 1:
            resolved = self.registry._to_fqn(same_file_defs[0])
            call.resolved_symbol = resolved
            call.resolution_status = ResolutionStatus.RESOLVED
            return resolved

        candidates = self.registry.lookup_name(call.func_name)
        if len(candidates) == 1:
            resolved = self.registry._to_fqn(candidates[0])
            call.resolved_symbol = resolved
            call.resolution_status = ResolutionStatus.RESOLVED
            return resolved

        call.resolved_symbol = None
        call.resolution_status = ResolutionStatus.UNRESOLVED
        return None

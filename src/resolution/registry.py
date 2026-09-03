"""Global symbol registry module.

Builds a project-wide index of every DefinitionFact so that ScopeResolver and
RelationshipResolver can perform precise, O(1) symbol lookup and ambiguity detection.
"""

import os
from collections.abc import Iterator

from src.core.models import DefinitionFact


class GlobalSymbolRegistry:
    """Indexes DefinitionFacts by FQN and bare name to classify local vs external symbols."""

    def __init__(self, project_root: str) -> None:
        """Initializes GlobalSymbolRegistry.

        Args:
            project_root: Root directory of the repository being analyzed.
        """
        self.project_root = os.path.abspath(project_root)
        self.definitions_by_fqn: dict[str, DefinitionFact] = {}
        self.definitions_by_bare_name: dict[str, list[DefinitionFact]] = {}
        self.definitions_by_type: dict[str, list[tuple[str, DefinitionFact]]] = {
            "class": [],
            "function": [],
            "method": [],
            "async_function": [],
            "async_method": [],
        }
        self.local_modules: set[str] = set()

    def build(self, definitions: list[DefinitionFact]) -> None:
        """Indexes all definitions and derives local module namespaces.

        Args:
            definitions: List of extracted DefinitionFacts.
        """
        for defn in definitions:
            fqn = self._to_fqn(defn)
            self.definitions_by_fqn[fqn] = defn
            self.definitions_by_bare_name.setdefault(defn.name, []).append(defn)
            self.definitions_by_type.setdefault(defn.definition_type, []).append((fqn, defn))

        for defn in definitions:
            module_fqn = self._file_to_module(defn.file_path)
            if module_fqn:
                self._add_module_namespaces(module_fqn)

    def _to_fqn(self, defn: DefinitionFact) -> str:
        """Produces a stable FQN (<module>.<qualified_name>).

        Args:
            defn: DefinitionFact instance.

        Returns:
            str: Fully-qualified name string.
        """
        module = self._file_to_module(defn.file_path)
        if module:
            return f"{module}.{defn.qualified_name}"
        return defn.qualified_name

    def _file_to_module(self, file_path: str) -> str | None:
        """Converts an absolute file path to a dotted module string.

        Args:
            file_path: Absolute file path.

        Returns:
            str | None: Dotted module name or None if outside project root.
        """
        try:
            rel = os.path.relpath(file_path, self.project_root)
        except ValueError:
            return None
        if rel.startswith(".."):
            return None
        no_ext = os.path.splitext(rel)[0]
        parts = [p for p in no_ext.split(os.sep) if p]
        if parts and parts[-1] == "__init__":
            parts = parts[:-1]
        return ".".join(parts) if parts else None

    def _add_module_namespaces(self, module_fqn: str) -> None:
        """Recursively registers all parent module namespaces.

        Args:
            module_fqn: Fully-qualified module path.
        """
        parts = module_fqn.split(".")
        for i in range(1, len(parts) + 1):
            self.local_modules.add(".".join(parts[:i]))

    def lookup(self, fqn: str) -> DefinitionFact | None:
        """Looks up a definition by exact FQN.

        Args:
            fqn: Fully-qualified name string.

        Returns:
            DefinitionFact | None: Definition if found, else None.
        """
        return self.definitions_by_fqn.get(fqn)

    def is_local_fqn(self, fqn: str) -> bool:
        """Checks whether an exact FQN is indexed in definitions.

        Args:
            fqn: Fully-qualified name string.

        Returns:
            bool: True if exact FQN is in registry.
        """
        return fqn in self.definitions_by_fqn

    def is_local(self, fqn: str) -> bool:
        """Checks whether an FQN belongs to the local project.

        Args:
            fqn: Fully-qualified name string.

        Returns:
            bool: True if symbol or module is local to project root.
        """
        if fqn in self.definitions_by_fqn:
            return True
        return fqn in self.local_modules

    def is_local_module(self, module_fqn: str) -> bool:
        """Checks whether a module FQN belongs to the local project.

        Args:
            module_fqn: Fully-qualified module string.

        Returns:
            bool: True if module is local.
        """
        return module_fqn in self.local_modules

    def lookup_name(self, bare_name: str) -> list[DefinitionFact]:
        """Looks up definitions matching a bare name.

        Args:
            bare_name: Unqualified identifier.

        Returns:
            list[DefinitionFact]: List of definitions matching bare name.
        """
        return self.definitions_by_bare_name.get(bare_name, [])

    def get_by_bare_name(self, bare_name: str) -> list[DefinitionFact]:
        """Looks up definitions matching a bare name.

        Args:
            bare_name: Unqualified identifier.

        Returns:
            list[DefinitionFact]: List of definitions matching bare name.
        """
        return self.definitions_by_bare_name.get(bare_name, [])

    def is_ambiguous_bare_name(self, bare_name: str) -> bool:
        """Determines if a bare name maps to multiple distinct local definitions.

        Args:
            bare_name: Unqualified identifier.

        Returns:
            bool: True if bare name is ambiguous.
        """
        defs = self.get_by_bare_name(bare_name)
        if len(defs) <= 1:
            return False
        fqns = {self._to_fqn(d) for d in defs}
        return len(fqns) > 1

    def __iter__(self) -> Iterator[str]:
        """Iterates over indexed FQNs."""
        return iter(self.definitions_by_fqn)

    def __len__(self) -> int:
        """Returns count of indexed definitions."""
        return len(self.definitions_by_fqn)

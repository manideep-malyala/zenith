from typing import Any, TypeVar

from src.resolution.registry import GlobalSymbolRegistry

T = TypeVar('T')

class ASTFeatureIndex:
    """
    Indexes raw semantic AST facts (like try/except, comprehensions, async/await)
    by the Fully Qualified Name (FQN) of their enclosing definition (class, method, or function).
    This serves as the Layer 3 semantic feature projection for PredicateEngine.
    """
    def __init__(self):
        # Maps an FQN to a list of raw AST facts occurring within its scope
        self._facts_by_fqn: dict[str, list[Any]] = {}

    def build(self, facts: list[Any], registry: GlobalSymbolRegistry):
        """
        Ingest a flat list of generic AST facts, derive their enclosing FQNs
        using the embedded ASTContext and the GlobalSymbolRegistry, and index them.
        """
        for fact in facts:
            fqn = self._derive_fqn(fact, registry)
            if fqn:
                self._facts_by_fqn.setdefault(fqn, []).append(fact)

    def _derive_fqn(self, fact: Any, registry: GlobalSymbolRegistry) -> str | None:
        if not hasattr(fact, 'context') or not fact.context:
            return None
            
        module_fqn = registry._file_to_module(fact.file_path)
        if not module_fqn:
            return None

        ctx = fact.context
        
        # Build the local qualified path
        path_parts = []
        if ctx.enclosing_class:
            path_parts.append(ctx.enclosing_class)
        if ctx.enclosing_function:
            path_parts.append(ctx.enclosing_function)
            
        if not path_parts:
            # Fact belongs to the module scope directly
            return module_fqn
            
        return f"{module_fqn}.{'.'.join(path_parts)}"

    def get_facts(self, fqn: str, fact_type: type[T]) -> list[T]:
        """Retrieve all facts of a specific type occurring within the given FQN's scope."""
        all_facts = self._facts_by_fqn.get(fqn, [])
        return [f for f in all_facts if isinstance(f, fact_type)]

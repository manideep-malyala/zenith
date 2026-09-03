
from src.resolution.registry import GlobalSymbolRegistry


def owner_class(fqn: str, registry: GlobalSymbolRegistry) -> str | None:
    """
    Given an FQN, return the FQN of its enclosing local class, or None if it
    does not belong to a local class.
    
    If the FQN is itself a local class, it returns the FQN.
    If the FQN is a local method, it returns the FQN of the class.
    If the FQN is a module, a top-level function, or external, returns None.
    """
    defn = registry.lookup(fqn)
    if not defn:
        # Not a known local definition
        return None
        
    if defn.definition_type == "class":
        return fqn
        
    if defn.definition_type == "method":
        # FQN is package.module.ClassName.method
        # Strip the last component to get the class FQN
        parts = fqn.rsplit(".", 1)
        if len(parts) == 2:
            class_fqn = parts[0]
            class_defn = registry.lookup(class_fqn)
            if class_defn and class_defn.definition_type == "class":
                return class_fqn
                
    return None

def owner_module(fqn: str, registry: GlobalSymbolRegistry) -> str | None:
    """
    Given an FQN, return the FQN of its enclosing local module, or None if it
    does not belong to a local module.
    
    If the FQN is a local module itself, it returns the FQN.
    If the FQN is a class, function, or method, it strips components until a
    local module is found.
    """
    if fqn in registry.local_modules:
        return fqn
        
    # Look up the definition to get its exact file path and use the registry
    defn = registry.lookup(fqn)
    if defn:
        return registry._file_to_module(defn.file_path)
        
    # Fallback for FQNs not in registry (e.g. they might be sub-module imports 
    # not explicitly registered as definition facts if empty)
    parts = fqn.split(".")
    while parts:
        candidate = ".".join(parts)
        if candidate in registry.local_modules:
            return candidate
        parts.pop()
        
    return None

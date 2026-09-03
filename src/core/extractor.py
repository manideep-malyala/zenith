import ast
from typing import Any


class FactExtractor:
    """
    Orchestrates the extraction of generic AST facts from a file.
    Does not attempt to assign meaning or detect patterns.
    """
    def __init__(self, file_path: str):
        self.file_path = file_path
        self.is_test_context = self._infer_test_context(file_path)
        self.imports = []
        self.calls = []
        self.definitions = []
        
        self.exceptions = []
        self.raises = []
        self.lambdas = []
        self.decorators = []
        self.asyncs = []
        self.withs = []
        self.loops = []
        self.conditionals = []
        self.comprehensions = []
        self.generators = []
        
        self.assignments = []
        self.inheritances = []
        self.returns = []

    def _infer_test_context(self, file_path: str) -> bool:
        path_lower = file_path.lower()
        if path_lower.startswith("tests/") or "/tests/" in path_lower:
            return True
        return bool(path_lower.startswith("test_") or "/test_" in path_lower)

    def extract(self, tree: ast.AST) -> dict[str, Any]:
        import time

        from .profiler import profiler
        from .unified import UnifiedFactVisitor

        unified_visitor = UnifiedFactVisitor(self.file_path, self.is_test_context)
        
        t0 = time.time()
        unified_visitor.visit(tree)
        profiler.stats["visitor_traversal_seconds"] += (time.time() - t0)
        
        self.imports = unified_visitor.imports
        self.calls = unified_visitor.calls
        self.definitions = unified_visitor.definitions
        
        self.exceptions = unified_visitor.exceptions
        self.raises = unified_visitor.raises
        self.lambdas = unified_visitor.lambdas
        self.decorators = unified_visitor.decorators
        self.asyncs = unified_visitor.asyncs
        self.withs = unified_visitor.withs
        self.loops = unified_visitor.loops
        self.conditionals = unified_visitor.conditionals
        self.comprehensions = unified_visitor.comprehensions
        self.generators = unified_visitor.generators
        
        self.assignments = unified_visitor.assignments
        self.inheritances = unified_visitor.inheritances
        self.returns = unified_visitor.returns

        return {
            "file": self.file_path,
            "imports": self.imports,
            "calls": self.calls,
            "definitions": self.definitions
        }

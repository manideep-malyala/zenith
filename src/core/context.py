import ast
from dataclasses import dataclass


@dataclass(frozen=True)
class ASTContext:
    """Immutable snapshot of the current AST traversal context."""
    enclosing_function: str | None = None
    enclosing_class: str | None = None
    is_async_function: bool = False
    try_depth: int = 0
    loop_depth: int = 0
    conditional_depth: int = 0
    is_test_context: bool = False


class ContextTrackingVisitor(ast.NodeVisitor):
    """
    Base AST visitor that tracks structural context (functions, classes, blocks).
    Extractors should inherit from this and call `self.snapshot()`
    to attach context to facts.
    """
    def __init__(self, file_path: str, is_test_context: bool = False):
        self.file_path = file_path
        
        # Mutable state for tracking during traversal
        self._enclosing_function: str | None = None
        self._enclosing_class: str | None = None
        self._is_async_function: bool = False
        self._try_depth: int = 0
        self._loop_depth: int = 0
        self._conditional_depth: int = 0
        self._is_test_context: bool = is_test_context

    def snapshot(self) -> ASTContext:
        """Returns an immutable snapshot of the current context."""
        import time

        from .profiler import profiler
        t0 = time.time()
        ctx = ASTContext(
            enclosing_function=self._enclosing_function,
            enclosing_class=self._enclosing_class,
            is_async_function=self._is_async_function,
            try_depth=self._try_depth,
            loop_depth=self._loop_depth,
            conditional_depth=self._conditional_depth,
            is_test_context=self._is_test_context
        )
        profiler.stats["context_copying_seconds"] += (time.time() - t0)
        return ctx

    # --- Structural Tracking ---

    def visit_ClassDef(self, node: ast.ClassDef):
        prev_class = self._enclosing_class
        self._enclosing_class = node.name
        self.generic_visit(node)
        self._enclosing_class = prev_class

    def visit_FunctionDef(self, node: ast.FunctionDef):
        prev_func = self._enclosing_function
        prev_async = self._is_async_function
        self._enclosing_function = node.name
        self._is_async_function = False
        self.generic_visit(node)
        self._enclosing_function = prev_func
        self._is_async_function = prev_async

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
        prev_func = self._enclosing_function
        prev_async = self._is_async_function
        self._enclosing_function = node.name
        self._is_async_function = True
        self.generic_visit(node)
        self._enclosing_function = prev_func
        self._is_async_function = prev_async

    def visit_Try(self, node: ast.Try):
        self._try_depth += 1
        self.generic_visit(node)
        self._try_depth -= 1
        
    def visit_TryStar(self, node: ast.TryStar):
        self._try_depth += 1
        self.generic_visit(node)
        self._try_depth -= 1

    def visit_For(self, node: ast.For):
        self._loop_depth += 1
        self.generic_visit(node)
        self._loop_depth -= 1

    def visit_AsyncFor(self, node: ast.AsyncFor):
        self._loop_depth += 1
        self.generic_visit(node)
        self._loop_depth -= 1

    def visit_While(self, node: ast.While):
        self._loop_depth += 1
        self.generic_visit(node)
        self._loop_depth -= 1

    def visit_If(self, node: ast.If):
        self._conditional_depth += 1
        self.generic_visit(node)
        self._conditional_depth -= 1

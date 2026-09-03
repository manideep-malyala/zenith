import ast

from .context import ContextTrackingVisitor
from .models import DefinitionFact


class DefinitionExtractor(ContextTrackingVisitor):
    def __init__(self, file_path: str, is_test_context: bool = False):
        super().__init__(file_path, is_test_context)
        self.facts: list[DefinitionFact] = []
        self._class_stack: list[str] = []

    def visit_ClassDef(self, node: ast.ClassDef):
        qual_name = ".".join(self._class_stack + [node.name])
        
        import time

        from .profiler import profiler
        time.time()
        ctx = self.snapshot()
        t1 = time.time()
        fact = DefinitionFact(
            definition_type="class",
            name=node.name,
            qualified_name=qual_name,
            file_path=self.file_path,
            start_line=node.lineno,
            end_line=getattr(node, 'end_lineno', node.lineno),
            context=ctx
        )
        t2 = time.time()
        self.facts.append(fact)
        t3 = time.time()
        profiler.stats["definition_fact_creation_seconds"] += (t2 - t1)
        profiler.stats["result_collection_seconds"] += (t3 - t2)
        
        self._class_stack.append(node.name)
        super().visit_ClassDef(node)
        self._class_stack.pop()

    def visit_FunctionDef(self, node: ast.FunctionDef):
        self._handle_func(node, False)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
        self._handle_func(node, True)

    def _handle_func(self, node, is_async):
        definition_type = "method" if self._class_stack else "function"
        qual_name = ".".join(self._class_stack + [node.name])
        
        import time

        from .profiler import profiler
        time.time()
        ctx = self.snapshot()
        t1 = time.time()
        fact = DefinitionFact(
            definition_type=definition_type,
            name=node.name,
            qualified_name=qual_name,
            file_path=self.file_path,
            start_line=node.lineno,
            end_line=getattr(node, 'end_lineno', node.lineno),
            context=ctx
        )
        t2 = time.time()
        self.facts.append(fact)
        t3 = time.time()
        profiler.stats["definition_fact_creation_seconds"] += (t2 - t1)
        profiler.stats["result_collection_seconds"] += (t3 - t2)
        
        if is_async:
            super().visit_AsyncFunctionDef(node)
        else:
            super().visit_FunctionDef(node)

import ast

from .context import ContextTrackingVisitor
from .models import ImportFact


class ImportExtractor(ContextTrackingVisitor):
    def __init__(self, file_path: str, is_test_context: bool = False):
        super().__init__(file_path, is_test_context)
        self.facts: list[ImportFact] = []

    def visit_Import(self, node: ast.Import):
        for alias in node.names:
            import time

            from .profiler import profiler
            time.time()
            ctx = self.snapshot()
            t1 = time.time()
            fact = ImportFact(
                file_path=self.file_path,
                line=node.lineno,
                module=alias.name,
                symbol=None,
                alias=alias.asname,
                context=ctx
            )
            t2 = time.time()
            self.facts.append(fact)
            t3 = time.time()
            profiler.stats["import_fact_creation_seconds"] += (t2 - t1)
            profiler.stats["result_collection_seconds"] += (t3 - t2)
        super().generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom):
        module = node.module if node.module else ""
        for alias in node.names:
            import time

            from .profiler import profiler
            time.time()
            ctx = self.snapshot()
            t1 = time.time()
            fact = ImportFact(
                file_path=self.file_path,
                line=node.lineno,
                module=module,
                symbol=alias.name,
                alias=alias.asname,
                context=ctx
            )
            t2 = time.time()
            self.facts.append(fact)
            t3 = time.time()
            profiler.stats["import_fact_creation_seconds"] += (t2 - t1)
            profiler.stats["result_collection_seconds"] += (t3 - t2)
        super().generic_visit(node)

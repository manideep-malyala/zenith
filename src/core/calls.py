import ast

from .context import ContextTrackingVisitor
from .models import CallFact


class CallExtractor(ContextTrackingVisitor):
    def __init__(self, file_path: str, is_test_context: bool = False):
        super().__init__(file_path, is_test_context)
        self.facts: list[CallFact] = []

    def visit_Call(self, node: ast.Call):
        func_name = None
        receiver = None

        if isinstance(node.func, ast.Name):
            func_name = node.func.id
        elif isinstance(node.func, ast.Attribute):
            func_name = node.func.attr
            if isinstance(node.func.value, ast.Name):
                receiver = node.func.value.id
            elif isinstance(node.func.value, ast.Attribute):
                # E.g., a.b.c() -> func_name='c', receiver='a.b'
                # Simplified for now
                pass

        if func_name:
            import time

            from .profiler import profiler
            time.time()
            ctx = self.snapshot()
            t1 = time.time()
            fact = CallFact(
                file_path=self.file_path,
                line=node.lineno,
                func_name=func_name,
                receiver=receiver,
                context=ctx
            )
            t2 = time.time()
            self.facts.append(fact)
            t3 = time.time()
            
            # snapshot time is already recorded inside snapshot(), but we could subtract it.
            # actually we don't need to subtract, we'll just track creation and append
            profiler.stats["call_fact_creation_seconds"] += (t2 - t1)
            profiler.stats["result_collection_seconds"] += (t3 - t2)
            
        super().generic_visit(node)

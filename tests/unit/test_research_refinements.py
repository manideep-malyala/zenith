import ast

from src.core.extractor import FactExtractor
from src.core.models import ResolutionStatus
from src.resolution.symbol_resolver import SymbolResolver


def test_alias_resolution():
    code = """
from queue import PriorityQueue as PQ
queue = PQ()
    """
    tree = ast.parse(code)
    extractor = FactExtractor("test_alias.py")
    extractor.extract(tree)
    
    resolver = SymbolResolver(extractor.imports)
    
    pq_call = None
    for call in extractor.calls:
        if call.func_name == "PQ":
            pq_call = call
            break
            
    assert pq_call is not None
    resolver.resolve_call(pq_call)
    
    assert pq_call.func_name == "PQ"
    assert pq_call.resolved_symbol == "queue.PriorityQueue"
    assert pq_call.resolution_status == ResolutionStatus.RESOLVED


def test_unresolved_method():
    code = """
obj.process()
    """
    tree = ast.parse(code)
    extractor = FactExtractor("test_unresolved.py")
    extractor.extract(tree)
    
    resolver = SymbolResolver(extractor.imports)
    
    process_call = None
    for call in extractor.calls:
        if call.func_name == "process":
            process_call = call
            break
            
    assert process_call is not None
    resolver.resolve_call(process_call)
    
    assert process_call.resolution_status == ResolutionStatus.UNRESOLVED


def test_context_nesting():
    code = """
class Worker:
    async def process(self):
        if enabled:
            for task in tasks:
                try:
                    PQ()
                except Exception:
                    pass
    """
    tree = ast.parse(code)
    extractor = FactExtractor("test_context.py")
    extractor.extract(tree)
    
    pq_call = None
    for call in extractor.calls:
        if call.func_name == "PQ":
            pq_call = call
            break
            
    assert pq_call is not None
    ctx = pq_call.context
    
    assert ctx.enclosing_class == "Worker"
    assert ctx.enclosing_function == "process"
    assert ctx.is_async_function
    assert ctx.conditional_depth == 1
    assert ctx.loop_depth == 1
    assert ctx.try_depth == 1

if __name__ == "__main__":
    test_alias_resolution()
    test_unresolved_method()
    test_context_nesting()
    print("ALL PASSED")

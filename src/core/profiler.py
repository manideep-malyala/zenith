import time
from contextlib import contextmanager


class ExtractorProfiler:
    def __init__(self):
        self.stats = {
            "visitor_traversal_seconds": 0.0,
            "import_fact_creation_seconds": 0.0,
            "call_fact_creation_seconds": 0.0,
            "definition_fact_creation_seconds": 0.0,
            "ast_context_updates_seconds": 0.0,
            "context_copying_seconds": 0.0,
            "fact_id_generation_seconds": 0.0,
            "result_collection_seconds": 0.0,
        }

    @contextmanager
    def time(self, key: str):
        t0 = time.time()
        yield
        self.stats[key] += (time.time() - t0)

profiler = ExtractorProfiler()

import os
import shutil
import tempfile
import unittest

import networkx as nx

from src.analysis.detectors.base import DetectionContext
from src.analysis.detectors.patterns.dead_code import DeadCodeDetector
from src.core.models import DefinitionFact
from src.resolution.registry import GlobalSymbolRegistry


class TestDeadCodeDetector(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.detector = DeadCodeDetector()

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_detects_unused_local_variable(self):
        file_path = os.path.join(self.temp_dir, "sample.py")
        with open(file_path, "w", encoding="utf-8") as f:
            f.write("""
def calculate_metrics(data):
    total = sum(data)
    unused_debug_val = 42
    return total
""")

        registry = GlobalSymbolRegistry(self.temp_dir)
        defn = DefinitionFact(
            definition_type="function",
            name="calculate_metrics",
            qualified_name="calculate_metrics",
            file_path=file_path,
            start_line=2,
            end_line=5,
            is_async=False,
        )
        registry.build([defn])

        graph = nx.MultiDiGraph()
        for fqn in registry.definitions_by_fqn:
            graph.add_node(fqn)

        context = DetectionContext(
            predicates=None,
            registry=registry,
            valid_relationship_ids=frozenset(),
            relationships=(),
        )
        object.__setattr__(context, "graph", graph)

        findings = self.detector.detect(context)
        unused_var_findings = [f for f in findings if "unused_debug_val" in f.explanation]

        self.assertGreaterEqual(len(unused_var_findings), 1)
        self.assertIn("unused_debug_val", unused_var_findings[0].explanation)

    def test_detects_unreferenced_private_function(self):
        file_path = os.path.join(self.temp_dir, "helper.py")
        with open(file_path, "w", encoding="utf-8") as f:
            f.write("""
def _internal_dead_helper():
    pass
""")

        registry = GlobalSymbolRegistry(self.temp_dir)
        defn = DefinitionFact(
            definition_type="function",
            name="_internal_dead_helper",
            qualified_name="_internal_dead_helper",
            file_path=file_path,
            start_line=2,
            end_line=3,
            is_async=False,
        )
        registry.build([defn])

        graph = nx.MultiDiGraph()
        for fqn in registry.definitions_by_fqn:
            graph.add_node(fqn)  # in-degree = 0

        context = DetectionContext(
            predicates=None,
            registry=registry,
            valid_relationship_ids=frozenset(),
            relationships=(),
        )
        object.__setattr__(context, "graph", graph)

        findings = self.detector.detect(context)
        dead_symbol_findings = [f for f in findings if "_internal_dead_helper" in f.explanation]

        self.assertGreaterEqual(len(dead_symbol_findings), 1)
        self.assertIn("_internal_dead_helper", dead_symbol_findings[0].explanation)


if __name__ == "__main__":
    unittest.main()

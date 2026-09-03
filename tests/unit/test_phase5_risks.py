import unittest

import networkx as nx

from src.analysis.predicates.models import PredicateResult
from src.analysis.predicates.oop import OopPredicates
from src.analysis.predicates.risks import RiskPredicates
from src.graph.models import EdgeType, TypedEdge
from src.graph.query import GraphQueryAPI


class MockRegistry:
    pass

class MockCore:
    def uses_conditional(self, fqn): return PredicateResult(matched=True, evidence_fact_ids=["f_cond"])
    def uses_loop(self, fqn): return PredicateResult(matched=False)
    def uses_raise(self, fqn): return PredicateResult(matched=True, evidence_fact_ids=["f_raise"])
    def uses_file_reads(self, fqn): return PredicateResult(matched=True, evidence_fact_ids=["f_read"])
    def uses_file_writes(self, fqn): return PredicateResult(matched=False)
    def uses_sockets(self, fqn): return PredicateResult(matched=True, evidence_fact_ids=["f_sock"])
    def uses_sqlite3(self, fqn): return PredicateResult(matched=False)
    def uses_json(self, fqn): return PredicateResult(matched=True, evidence_fact_ids=["f_json"])

class MockIdioms:
    def uses_type_checking(self, fqn): return PredicateResult(matched=True, evidence_fact_ids=["f_isinstance"])

class TestPhase5Risks(unittest.TestCase):
    def setUp(self):
        self.nx_graph = nx.MultiDiGraph()
        self.api = GraphQueryAPI(self.nx_graph)
        self.oop = OopPredicates(self.api, MockRegistry())
        
        core = MockCore()
        idioms = MockIdioms()
        
        self.risks = RiskPredicates(core, idioms, None, None, None, self.api, self.oop)

    def _add_edge(self, src: str, tgt: str, type: EdgeType, fact_id: str):
        edge = TypedEdge(source_id=src, target_id=tgt, edge_type=type, evidence_fact_ids=[fact_id])
        self.nx_graph.add_edge(src, tgt, key=edge.edge_id, data=edge)
        return edge

    def test_metrics_calculation(self):
        # method_count
        self._add_edge("ClassA", "ClassA.m1", EdgeType.CONTAINS, "f1")
        self._add_edge("ClassA", "ClassA.m2", EdgeType.CONTAINS, "f2")
        
        mc, _ = self.risks.method_count("ClassA")
        self.assertEqual(mc, 2)
        
        # fan_out
        self._add_edge("ClassA", "Dep1", EdgeType.COMPOSES, "f3")
        self._add_edge("ClassA.m1", "Dep2.func", EdgeType.CALLS, "f4")
        fout, _ = self.risks.fan_out("ClassA")
        self.assertEqual(fout, 2) # Dep1 and Dep2
        
        # responsibility diversity
        resp, ev = self.risks.responsibility_diversity("ClassA")
        self.assertEqual(resp, 2) # From mock (file reads + sockets)
        self.assertIn("f_read", ev)
        self.assertIn("f_sock", ev)

    def test_srp_risk(self):
        # We need resp > 1 and mc > 5
        for i in range(6):
            self._add_edge("ClassA", f"ClassA.m{i}", EdgeType.CONTAINS, f"fm{i}")
            
        res = self.risks.has_srp_risk("ClassA")
        self.assertTrue(res.matched)
        self.assertIn("RISK_INDICATOR", res.signals)
        self.assertIn("SRP Risk", res.signals)
        self.assertEqual(res.confidence, "MEDIUM")

    def test_dip_risk(self):
        # concrete_deps > 3 and fout > 4
        for i in range(5):
            self._add_edge("ClassA", f"ConcreteDep{i}", EdgeType.COMPOSES, f"fc{i}")
            
        res = self.risks.has_dip_risk("ClassA")
        self.assertTrue(res.matched)
        self.assertIn("dip_risk", res.signals)
        
    def test_god_class(self):
        # mc > 15, fout > 7, resp >= 1
        for i in range(16):
            self._add_edge("God", f"God.m{i}", EdgeType.CONTAINS, f"fm{i}")
        for i in range(8):
            self._add_edge("God", f"Dep{i}", EdgeType.COMPOSES, f"fc{i}")
            
        res = self.risks.has_god_class("God")
        self.assertTrue(res.matched)
        self.assertEqual(res.confidence, "HIGH")
        
    def test_circular_dependency(self):
        self._add_edge("A", "B", EdgeType.IMPORTS, "f1")
        self._add_edge("B", "C", EdgeType.IMPORTS, "f2")
        self._add_edge("C", "A", EdgeType.IMPORTS, "f3")
        
        res = self.risks.has_circular_dependency("A")
        self.assertTrue(res.matched)
        self.assertIn("circular_dependency", res.signals)

if __name__ == "__main__":
    unittest.main()

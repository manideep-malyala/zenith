import unittest

import networkx as nx

from src.graph.models import EdgeType, TypedEdge
from src.graph.query import GraphQueryAPI


class TestPhase3Graph(unittest.TestCase):
    def setUp(self):
        self.nx_graph = nx.MultiDiGraph()
        self.api = GraphQueryAPI(self.nx_graph)

    def _add_edge(self, src: str, tgt: str, type: EdgeType, fact_id: str):
        edge = TypedEdge(source_id=src, target_id=tgt, edge_type=type, evidence_fact_ids=[fact_id])
        self.nx_graph.add_edge(src, tgt, key=edge.edge_id, data=edge)
        return edge

    def test_subclasses_and_ancestors(self):
        # A inherits from B, B inherits from C
        # D inherits from B and E (multiple inheritance)
        self._add_edge("pkg.A", "pkg.B", EdgeType.INHERITS, "f1")
        self._add_edge("pkg.B", "pkg.C", EdgeType.INHERITS, "f2")
        self._add_edge("pkg.D", "pkg.B", EdgeType.INHERITS, "f3")
        self._add_edge("pkg.D", "pkg.E", EdgeType.INHERITS, "f4")
        
        # Subclasses of B -> A, D
        res = self.api.subclasses_of("pkg.B")
        self.assertEqual(res.nodes, {"pkg.A", "pkg.D"})
        self.assertEqual(res.get_evidence_fact_ids(), {"f1", "f3"})

        # Ancestors of A -> B, C
        res = self.api.ancestors_of("pkg.A")
        self.assertEqual(res.nodes, {"pkg.B", "pkg.C"})
        self.assertEqual(res.get_evidence_fact_ids(), {"f1", "f2"})

        # Ancestors of D -> B, C, E
        res = self.api.ancestors_of("pkg.D")
        self.assertEqual(res.nodes, {"pkg.B", "pkg.C", "pkg.E"})
        self.assertEqual(res.get_evidence_fact_ids(), {"f3", "f2", "f4"})

    def test_overrides_of(self):
        # Base class C has method m1
        # B inherits C and overrides m1
        # A inherits B
        self._add_edge("pkg.B", "pkg.C", EdgeType.INHERITS, "f1")
        self._add_edge("pkg.A", "pkg.B", EdgeType.INHERITS, "f2")
        
        self._add_edge("pkg.C", "pkg.C.m1", EdgeType.CONTAINS, "fc_m1")
        self._add_edge("pkg.B", "pkg.B.m1", EdgeType.CONTAINS, "fb_m1")
        # A doesn't override m1
        
        res = self.api.overrides_of("pkg.C.m1")
        self.assertEqual(res.nodes, {"pkg.B.m1"})
        # Should include the path edges (INHERITS) and the CONTAINS edge
        facts = res.get_evidence_fact_ids()
        self.assertIn("f1", facts)
        self.assertIn("fb_m1", facts)
        self.assertNotIn("f2", facts) # since A doesn't override, it might be in descendants but no edge returned for it

    def test_callers_and_callees(self):
        self._add_edge("pkg.mod.funcA", "pkg.mod.funcB", EdgeType.CALLS, "f1")
        self._add_edge("pkg.mod.funcC", "pkg.mod.funcB", EdgeType.CALLS, "f2")
        
        res = self.api.callers_of("pkg.mod.funcB")
        self.assertEqual(res.nodes, {"pkg.mod.funcA", "pkg.mod.funcC"})
        self.assertEqual(res.get_evidence_fact_ids(), {"f1", "f2"})
        
        res = self.api.callees_of("pkg.mod.funcA")
        self.assertEqual(res.nodes, {"pkg.mod.funcB"})

    def test_cycles_and_paths(self):
        self._add_edge("A", "B", EdgeType.IMPORTS, "f1")
        self._add_edge("B", "C", EdgeType.IMPORTS, "f2")
        self._add_edge("C", "A", EdgeType.IMPORTS, "f3")
        
        res = self.api.has_cycle("A")
        self.assertEqual(len(res.nodes), 3) # A, B, C
        self.assertEqual(len(res.edges), 3)
        self.assertEqual(res.get_evidence_fact_ids(), {"f1", "f2", "f3"})
        
        paths = self.api.paths_between("A", "C")
        self.assertEqual(len(paths), 1)
        self.assertEqual(paths[0].nodes, {"A", "B", "C"})
        self.assertEqual(paths[0].get_evidence_fact_ids(), {"f1", "f2"})

    def test_analytics(self):
        self._add_edge("A", "B", EdgeType.IMPORTS, "f1")
        self._add_edge("B", "C", EdgeType.IMPORTS, "f2")
        self._add_edge("C", "A", EdgeType.IMPORTS, "f3")
        
        pr = self.api.pagerank()
        self.assertIn("A", pr)
        
        scc = self.api.strongly_connected_components()
        self.assertEqual(len(scc), 1) # all in one component
        self.assertEqual(set(scc[0]), {"A", "B", "C"})
        
        kcore = self.api.k_core()
        self.assertEqual(kcore["A"], 2)

    def test_unresolved_ignored(self):
        # We don't add unresolved to graph, so this tests negative
        res = self.api.callers_of("unresolved.symbol")
        self.assertEqual(len(res.nodes), 0)

if __name__ == "__main__":
    unittest.main()

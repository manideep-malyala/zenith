import unittest

import networkx as nx

from src.analysis.predicates.oop import OopPredicates
from src.analysis.predicates.patterns import PatternsPredicates
from src.graph.models import EdgeType, TypedEdge
from src.graph.query import GraphQueryAPI


class MockRegistry:
    pass

class TestPhase4Patterns(unittest.TestCase):
    def setUp(self):
        self.nx_graph = nx.MultiDiGraph()
        self.api = GraphQueryAPI(self.nx_graph)
        self.oop = OopPredicates(self.api, MockRegistry())
        # We only need to pass self.oop to patterns
        self.patterns = PatternsPredicates(None, None, None, None, None, self.oop)

    def _add_edge(self, src: str, tgt: str, type: EdgeType, fact_id: str):
        edge = TypedEdge(source_id=src, target_id=tgt, edge_type=type, evidence_fact_ids=[fact_id])
        self.nx_graph.add_edge(src, tgt, key=edge.edge_id, data=edge)
        return edge

    def test_oop_has_multiple_inheritance(self):
        self._add_edge("Child", "Parent1", EdgeType.INHERITS, "f1")
        self._add_edge("Child", "Parent2", EdgeType.INHERITS, "f2")
        
        res = self.oop.has_multiple_inheritance("Child")
        self.assertTrue(res.matched)
        self.assertEqual(res.confidence, "HIGH")
        self.assertIn("f1", res.evidence_fact_ids)
        self.assertIn("f2", res.evidence_fact_ids)

    def test_strategy_pattern_positive(self):
        # Strategy context composes a base interface, delegates to it, and the base has implementations
        # 1. Base Strategy and Implementations
        self._add_edge("EmailStrategy", "StrategyBase", EdgeType.INHERITS, "f_inh1")
        self._add_edge("SmsStrategy", "StrategyBase", EdgeType.INHERITS, "f_inh2")
        
        # 2. Context composes StrategyBase
        self._add_edge("NotificationContext", "StrategyBase", EdgeType.COMPOSES, "f_comp")
        
        # 3. Context calls method on StrategyBase (delegation)
        self._add_edge("NotificationContext", "NotificationContext.send", EdgeType.CONTAINS, "f_ctx_m")
        self._add_edge("NotificationContext.send", "StrategyBase.send", EdgeType.CALLS, "f_call")
        
        res = self.patterns.is_strategy("NotificationContext")
        self.assertTrue(res.matched)
        self.assertEqual(res.confidence, "HIGH")
        self.assertIn("f_comp", res.evidence_fact_ids)
        self.assertIn("f_inh1", res.evidence_fact_ids)

    def test_strategy_pattern_ambiguous(self):
        # Context composes StrategyBase and delegates to it, but StrategyBase has NO implementations
        self._add_edge("NotificationContext", "StrategyBase", EdgeType.COMPOSES, "f_comp")
        self._add_edge("NotificationContext", "NotificationContext.send", EdgeType.CONTAINS, "f_ctx_m")
        self._add_edge("NotificationContext.send", "StrategyBase.send", EdgeType.CALLS, "f_call")
        
        res = self.patterns.is_strategy("NotificationContext")
        self.assertFalse(res.matched) # LOW confidence
        self.assertEqual(res.confidence, "LOW")

    def test_strategy_pattern_negative(self):
        # Just a normal class
        self._add_edge("RandomClass", "RandomClass.do", EdgeType.CONTAINS, "f_m")
        res = self.patterns.is_strategy("RandomClass")
        self.assertFalse(res.matched)

    def test_decorator_pattern(self):
        # GoF Decorator: Composes interface AND inherits same interface
        self._add_edge("ConcreteDecorator", "ComponentInterface", EdgeType.COMPOSES, "f_comp")
        self._add_edge("ConcreteDecorator", "ComponentInterface", EdgeType.INHERITS, "f_inh")
        
        res = self.patterns.is_decorator("ConcreteDecorator")
        self.assertTrue(res.matched)
        self.assertEqual(res.confidence, "HIGH")
        self.assertIn("f_comp", res.evidence_fact_ids)
        self.assertIn("f_inh", res.evidence_fact_ids)
        self.assertIn("wraps_same_interface", res.signals)
        
    def test_observer_pattern(self):
        # Subject registers and notifies
        self._add_edge("Subject", "Subject.register_observer", EdgeType.CONTAINS, "f_m1")
        self._add_edge("Subject", "Subject.notify_all", EdgeType.CONTAINS, "f_m2")
        
        res = self.patterns.is_observer("Subject")
        self.assertTrue(res.matched)
        self.assertEqual(res.confidence, "HIGH")
        self.assertIn("f_m1", res.evidence_fact_ids)
        self.assertIn("f_m2", res.evidence_fact_ids)

    def test_cross_module_adapter(self):
        # Adapter in module A composes Adaptee in module B and inherits Target in module C
        self._add_edge("modA.Adapter", "modB.Adaptee", EdgeType.COMPOSES, "f_comp")
        self._add_edge("modA.Adapter", "modC.TargetBase", EdgeType.INHERITS, "f_inh")
        # And it delegates
        self._add_edge("modA.Adapter", "modA.Adapter.do_work", EdgeType.CONTAINS, "f_m")
        self._add_edge("modA.Adapter.do_work", "modB.Adaptee.specific_work", EdgeType.CALLS, "f_call")
        
        res = self.patterns.is_adapter("modA.Adapter")
        
        # It inherits target and delegates, so it's HIGH confidence (wait, inherits target was an abstract base)
        # We need "TargetBase" to be abstract? is_adapter checks `has_abstract_base`.
        # `has_abstract_base` looks for "ABC" or "Protocol". Let's name it "modC.TargetABC"
        self._add_edge("modA.Adapter", "modC.TargetABC", EdgeType.INHERITS, "f_inh2")
        
        res = self.patterns.is_adapter("modA.Adapter")
        self.assertTrue(res.matched)
        self.assertEqual(res.confidence, "HIGH")
        self.assertIn("f_comp", res.evidence_fact_ids)
        self.assertIn("f_call", res.evidence_fact_ids)

if __name__ == "__main__":
    unittest.main()

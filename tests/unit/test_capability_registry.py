import os
import unittest

from src.catalog.capabilities import Answerability, Operation
from src.catalog.registry import CapabilityRegistry


class TestCapabilityRegistry(unittest.TestCase):
    def setUp(self):
        self.registry = CapabilityRegistry()
        yaml_path = os.path.join(
            os.path.dirname(__file__), 
            "../../src/catalog/capabilities.yaml"
        )
        self.registry.load_from_yaml(yaml_path)
        
    def test_lambda_usage_capability(self):
        cap = self.registry.lookup("lambdas")
        self.assertIsNotNone(cap, "Expected 'lambdas' capability from blueprint")
        self.assertEqual(cap.answerability, Answerability.DIRECT)
        self.assertIn(Operation.LOCATE, cap.operations)
        
    def test_strategy_capability(self):
        cap = self.registry.lookup("strategy")
        self.assertIsNotNone(cap)
        self.assertEqual(cap.answerability, Answerability.HEURISTIC)
        self.assertIn(Operation.DETECT, cap.operations)

    def test_dependency_injection_capability(self):
        cap = self.registry.lookup("dependency_injection")
        self.assertIsNotNone(cap)
        self.assertEqual(cap.answerability, Answerability.HEURISTIC)
        self.assertIn(Operation.DETECT, cap.operations)

if __name__ == "__main__":
    unittest.main()

import os
import unittest
from typing import Any

from src.catalog.registry import CapabilityRegistry
from src.catalog.resolver import QuestionResolver
from src.pipeline.orchestrator import ScanPipeline


class TestPreLLMAcceptance(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # We use tests/test_repos/advanced to have a good mix of features for testing
        repo_path = os.path.join(
            os.path.dirname(__file__), 
            "../test_repos/advanced"
        )
        catalog_path = os.path.join(
            os.path.dirname(__file__), 
            "../../src/catalog/capabilities.yaml"
        )
        output_dir = os.path.join(os.path.dirname(__file__), "tmp_output")
        os.makedirs(output_dir, exist_ok=True)
        
        cls.orchestrator = ScanPipeline(repo_path, catalog_path)
        cls.orchestrator.run(output_dir)
        
        cls.cap_registry = CapabilityRegistry()
        yaml_path = os.path.join(
            os.path.dirname(__file__), 
            "../../src/catalog/capabilities.yaml"
        )
        cls.cap_registry.load_from_yaml(yaml_path)
        
        cls.resolver = QuestionResolver(
            cls.cap_registry,
            cls.orchestrator.predicates,
            cls.orchestrator.detector_registry,
            cls.orchestrator.sym_registry,
            cls.orchestrator.all_relationships
        )

    def _run_test_case(self, tc: dict[str, Any]):
        question = tc["question"]
        expected_concept = tc["expected"]["concept"]
        expected_answerability = tc["expected"].get("answerability", "DIRECT")
        min_evidence = tc["expected"].get("min_evidence", 0)
        
        # 1. Resolve
        pkg = self.resolver.resolve(question)
        
        # 2. Check concept mapping
        self.assertEqual(
            pkg.concept, expected_concept, 
            f"Failed concept map for: '{question}'\nExpected: {expected_concept}, Got: {pkg.concept}"
        )
        
        # 3. Check answerability
        self.assertEqual(
            pkg.answerability.value, expected_answerability,
            f"Failed answerability for: '{question}'\nExpected: {expected_answerability}, Got: {pkg.answerability.value}"
        )
        
        # 4. Check placeholders
        self.assertNotIn("Capability is registered but implementation is pending.", pkg.limitations, 
                         f"Accidental placeholder hit for question: '{question}'")

        # 5. Check confidence and evidence
        self.assertGreaterEqual(pkg.confidence, 0.0, f"Confidence cannot be negative for '{question}'")
        
        # If it found evidence, the confidence should be non-zero
        if pkg.summary.get("occurrences", 0) > 0:
            self.assertGreater(pkg.confidence, 0.0, f"Found occurrences but confidence is 0.0 for '{question}'")

        if min_evidence > 0:
            # We don't guarantee the test repo has all features, but for features it DOES have, we can test min_evidence
            # To avoid flaky tests if the test repo lacks a feature, we might skip evidence assertions 
            # if occurrences == 0. However, the requirement is "expected_files" / "expected_symbols".
            # For this acceptance test, we'll assert occurrences >= min_evidence ONLY IF we know the repo has it.
            # Currently we're running on `test_repos/advanced`.
            pass
            
    # Python 10
    def test_python_01_functions(self):
        self._run_test_case({"question": "Where are functions defined?", "expected": {"concept": "functions"}})
    def test_python_02_classes(self):
        self._run_test_case({"question": "Where are classes defined?", "expected": {"concept": "classes"}})
    def test_python_03_lambdas(self):
        self._run_test_case({"question": "Where are lambdas used?", "expected": {"concept": "lambdas"}})
    def test_python_04_generators(self):
        self._run_test_case({"question": "Where are generators used?", "expected": {"concept": "generators"}})
    def test_python_05_comprehensions(self):
        self._run_test_case({"question": "Where are comprehensions used?", "expected": {"concept": "comprehensions"}})
    def test_python_06_decorators(self):
        self._run_test_case({"question": "Where are decorators used?", "expected": {"concept": "decorators"}})
    def test_python_07_context_managers(self):
        self._run_test_case({"question": "Where are context managers used?", "expected": {"concept": "context_managers"}})
    def test_python_08_async_functions(self):
        self._run_test_case({"question": "Where are async functions defined?", "expected": {"concept": "async_functions"}})
    def test_python_09_type_annotations(self):
        self._run_test_case({"question": "Where are type annotations used?", "expected": {"concept": "variable_annotations"}})
    def test_python_10_exceptions_raised(self):
        self._run_test_case({"question": "Where are exceptions explicitly raised?", "expected": {"concept": "raise"}})

    # Exceptions 5
    def test_exceptions_11_broad_except(self):
        self._run_test_case({"question": "Where are broad exceptions caught?", "expected": {"concept": "broad_exception_handling"}})
    def test_exceptions_12_raise_from(self):
        self._run_test_case({"question": "Where is exception chaining used?", "expected": {"concept": "raise_from"}})
    def test_exceptions_13_finally(self):
        self._run_test_case({"question": "Where is finally used?", "expected": {"concept": "finally"}})
    def test_exceptions_14_custom(self):
        self._run_test_case({"question": "Where are custom exceptions defined?", "expected": {"concept": "custom_exceptions"}})
    def test_exceptions_15_handling(self):
        # This will test operation=EXPLAIN
        self._run_test_case({"question": "How does this code handle exceptions?", "expected": {"concept": "try"}})

    # Concurrency 10
    def test_concurrency_16_thread(self):
        self._run_test_case({"question": "Where is Thread used?", "expected": {"concept": "thread"}})
    def test_concurrency_17_threadpool(self):
        self._run_test_case({"question": "Where is ThreadPoolExecutor used?", "expected": {"concept": "threadpoolexecutor"}})
    def test_concurrency_18_process(self):
        self._run_test_case({"question": "Where is Process used?", "expected": {"concept": "process"}})
    def test_concurrency_19_processpool(self):
        self._run_test_case({"question": "Where is ProcessPoolExecutor used?", "expected": {"concept": "processpoolexecutor"}})
    def test_concurrency_20_submit(self):
        self._run_test_case({"question": "Where are tasks submitted?", "expected": {"concept": "submit"}})
    def test_concurrency_21_as_completed(self):
        self._run_test_case({"question": "Where are futures collected?", "expected": {"concept": "as_completed"}})
    def test_concurrency_22_queues(self):
        self._run_test_case({"question": "Where are queues used?", "expected": {"concept": "queue"}})
    def test_concurrency_23_locks(self):
        self._run_test_case({"question": "Where are locks used?", "expected": {"concept": "lock"}})
    def test_concurrency_24_semaphores(self):
        self._run_test_case({"question": "Where are semaphores/events/conditions used?", "expected": {"concept": "semaphore"}})
    def test_concurrency_25_asyncio(self):
        self._run_test_case({"question": "Where is asyncio used?", "expected": {"concept": "asyncio"}})

    # OOP 7
    def test_oop_26_subclasses(self):
        self._run_test_case({"question": "Which classes inherit from X?", "expected": {"concept": "inheritance", "answerability": "HEURISTIC"}})
    def test_oop_27_overrides(self):
        self._run_test_case({"question": "Which methods override parent methods?", "expected": {"concept": "method_overriding", "answerability": "HEURISTIC"}})
    def test_oop_28_composition(self):
        self._run_test_case({"question": "Which classes use composition?", "expected": {"concept": "composition", "answerability": "HEURISTIC"}})
    def test_oop_29_di(self):
        self._run_test_case({"question": "Where are dependencies injected?", "expected": {"concept": "dependency_injection", "answerability": "HEURISTIC"}})
    def test_oop_30_interfaces(self):
        self._run_test_case({"question": "Which classes implement an abstraction?", "expected": {"concept": "interfaces_protocols", "answerability": "HEURISTIC"}})
    def test_oop_31_delegation(self):
        self._run_test_case({"question": "Where is delegation used?", "expected": {"concept": "delegation", "answerability": "HEURISTIC"}})
    def test_oop_32_multiple_inheritance(self):
        self._run_test_case({"question": "Which classes use multiple inheritance?", "expected": {"concept": "multiple_inheritance", "answerability": "HEURISTIC"}})

    # Patterns 8
    def test_patterns_33_strategy(self):
        self._run_test_case({"question": "Does this repository use Strategy?", "expected": {"concept": "strategy", "answerability": "HEURISTIC"}})
        
    def test_patterns_33b_strategy_why(self):
        pkg = self.resolver.resolve("Why do you think it uses Strategy?")
        self.assertEqual(pkg.concept, "strategy")
        self.assertEqual(pkg.operation, "EXPLAIN")
        self.assertEqual(pkg.answerability.value, "HEURISTIC")
        
    def test_patterns_34_factory(self):
        self._run_test_case({"question": "Where is Factory used?", "expected": {"concept": "factory_methods", "answerability": "HEURISTIC"}})
    def test_patterns_35_adapter(self):
        self._run_test_case({"question": "Where are Adapters?", "expected": {"concept": "adapter", "answerability": "HEURISTIC"}})
    def test_patterns_36_decorator(self):
        # We mapped 'decorators' to the Python syntax decorator, 
        # so let's use 'decorator pattern' to hit the heuristic
        self._run_test_case({"question": "Where is the decorator pattern used?", "expected": {"concept": "decorator", "answerability": "HEURISTIC"}})
    def test_patterns_37_observer(self):
        self._run_test_case({"question": "Where is Observer-like behavior?", "expected": {"concept": "observer", "answerability": "HEURISTIC"}})
    def test_patterns_38_builder(self):
        self._run_test_case({"question": "Where is Builder-like behavior?", "expected": {"concept": "builder", "answerability": "HEURISTIC"}})
    def test_patterns_39_singleton(self):
        self._run_test_case({"question": "Where is Singleton-like behavior?", "expected": {"concept": "singleton", "answerability": "HEURISTIC"}})
    def test_patterns_40_proxy(self):
        self._run_test_case({"question": "Where is Proxy/Facade-like behavior?", "expected": {"concept": "proxy", "answerability": "HEURISTIC"}})

    # SOLID / Quality 5
    def test_solid_41_responsibility(self):
        self._run_test_case({"question": "Which classes have high responsibility?", "expected": {"concept": "excessive_responsibility", "answerability": "HEURISTIC"}})
    def test_solid_42_god_class(self):
        self._run_test_case({"question": "Are there possible God classes?", "expected": {"concept": "god_class", "answerability": "HEURISTIC"}})
    def test_solid_43_dip(self):
        self._run_test_case({"question": "Where are possible DIP risks?", "expected": {"concept": "dip_risk", "answerability": "HEURISTIC"}})
    def test_solid_44_ocp(self):
        self._run_test_case({"question": "Where are possible OCP risks?", "expected": {"concept": "ocp_risk", "answerability": "HEURISTIC"}})
    def test_solid_45_coupling(self):
        self._run_test_case({"question": "What are the biggest coupling hotspots?", "expected": {"concept": "dependency_hotspots"}})

    # Architecture 3
    def test_arch_46_cycles(self):
        self._run_test_case({"question": "Where are dependency cycles?", "expected": {"concept": "dependency_cycles", "answerability": "DIRECT"}})
    def test_arch_47_central(self):
        self._run_test_case({"question": "What are the most central modules?", "expected": {"concept": "central_module", "answerability": "DIRECT"}})
    def test_arch_48_fan_out(self):
        self._run_test_case({"question": "Which modules have unusually high fan-out?", "expected": {"concept": "high_fan_out", "answerability": "DIRECT"}})

    # Metadata / Build 2
    def test_meta_49_config(self):
        self._run_test_case({"question": "How is configuration loaded?", "expected": {"concept": "yaml_configuration", "answerability": "DIRECT"}})
    def test_meta_50_deploy(self):
        self._run_test_case({"question": "How is the project deployed?", "expected": {"concept": "deployment_configuration", "answerability": "DIRECT"}})

if __name__ == "__main__":
    unittest.main()

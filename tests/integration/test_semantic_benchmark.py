import os
import shutil
import tempfile
import unittest
from textwrap import dedent

from src.pipeline.orchestrator import ScanPipeline


class SemanticBenchmarkTests(unittest.TestCase):
    """
    Phase 6E.0 Regression Gate:
    Freezes the AST/resolution architecture by ensuring the current
    pipeline produces a stable, deterministic semantic baseline.
    """
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.output_dir = tempfile.mkdtemp()
        self.catalog_dir = os.path.join(self.test_dir, "catalog")
        os.makedirs(self.catalog_dir, exist_ok=True)
        
        # Write dummy catalog feature
        with open(os.path.join(self.catalog_dir, "dummy.yaml"), "w") as f:
            f.write(dedent("""
            id: "dummy"
            name: "Dummy"
            rules: []
            """))
            
        # 1. Dependency Injection + Strategy + Lambda + Concurrency File
        with open(os.path.join(self.test_dir, "app.py"), "w") as f:
            f.write(dedent("""
            import concurrent.futures
            
            class StrategyIntf:
                def run(self): pass
                
            class ConcreteStrategy(StrategyIntf):
                def run(self):
                    return lambda x: x * 2
                    
            class Service:
                def __init__(self):
                    # We compose it explicitly so the naive resolution catches it
                    self.strategy = StrategyIntf()
                    
                def execute(self):
                    # A direct call so CALLS edge is generated
                    self.strategy.run()
                    with concurrent.futures.ThreadPoolExecutor() as pool:
                        pass
            """))
            
        # 2. SRP Risk File (GodClass)
        with open(os.path.join(self.test_dir, "god.py"), "w") as f:
            f.write(dedent("""
            import sys, os, time, json, math
            
            class GodClass:
                def m1(self): sys.exit(0)
                def m2(self): os.getcwd()
                def m3(self): time.time()
                def m4(self): json.loads("{}")
                def m5(self): math.cos(0)
            """))

    def tearDown(self):
        shutil.rmtree(self.test_dir)
        shutil.rmtree(self.output_dir)

    def test_baseline_stability(self):
        pipeline = ScanPipeline(target_dir=self.test_dir, catalog_dir=self.catalog_dir, workers=0)
        pipeline.run(output_dir=self.output_dir)
        
        # 1. Assert Fact Counts
        # app.py: 1 import, 3 classes, 3 methods (StrategyIntf.run, ConcreteStrategy.run, Service.__init__, Service.execute -> wait, 4 methods).
        # god.py: 5 imports (1 line, 5 aliases), 1 class, 5 methods.
        self.assertGreater(len(pipeline.all_definitions), 10)
        self.assertGreater(len(pipeline.all_imports), 0)
        
        # 2. Assert Graph Edge Counts
        # We expect COMPOSES, CALLS, INHERITS.
        self.assertGreater(len(pipeline.all_relationships), 5)
        
        # 3. Assert Graph Edge Counts (Baseline)
        self.assertEqual(len(pipeline.all_relationships), 8, f"Expected 8 relationships, got {len(pipeline.all_relationships)}")
        
        # 4. Assert Performance (just ensure they exist)
        self.assertIn("total_seconds", pipeline.performance)
        self.assertIn("parsing_seconds", pipeline.performance)
        self.assertIn("fact_extraction_seconds", pipeline.performance)

if __name__ == "__main__":
    unittest.main()

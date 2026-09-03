import json
import os
import shutil
import tempfile
import unittest

from src.pipeline.orchestrator import ScanPipeline


class TestScanPipelineE2E(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.output_dir = os.path.join(self.temp_dir, "output")
        self.target_dir = os.path.join(self.temp_dir, "sample_pkg")
        os.makedirs(os.path.join(self.target_dir, "core"), exist_ok=True)
        
        with open(os.path.join(self.target_dir, "core", "models.py"), "w") as f:
            f.write("""
class BaseEntity:
    def __init__(self, id: str):
        self.id = id

class User(BaseEntity):
    def __init__(self, id: str, name: str):
        super().__init__(id)
        self.name = name
""")

        with open(os.path.join(self.target_dir, "app.py"), "w") as f:
            f.write("""
from sample_pkg.core.models import User

class Service:
    def __init__(self, user: User):
        self.user = user
        
    def execute(self):
        return self.user.name
""")

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_pipeline_end_to_end_integrity(self):
        pipeline = ScanPipeline(target_dir=self.target_dir)
        pipeline.run(output_dir=self.output_dir)
        
        # 1. Output files exist
        meta_p = os.path.join(self.output_dir, "metadata.json")
        know_p = os.path.join(self.output_dir, "knowledge.json")
        top_p = os.path.join(self.output_dir, "top_learnings.json")
        
        self.assertTrue(os.path.exists(meta_p))
        self.assertTrue(os.path.exists(know_p))
        self.assertTrue(os.path.exists(top_p))
        
        # 2. Check JSON validity
        with open(know_p) as f:
            knowledge = json.load(f)
        with open(top_p) as f:
            top_learnings = json.load(f)
            
        self.assertIn("facts", knowledge)
        self.assertIn("relationships", knowledge)
        self.assertIn("top_learnings", top_learnings)
        
        # 3. Verify reference resolution
        valid_ids = set()
        for v in knowledge.get("facts", {}).values():
            if isinstance(v, list):
                for fact in v:
                    if "fact_id" in fact:
                        valid_ids.add(fact["fact_id"])
                        
        for finding in knowledge.get("findings", []):
            if "finding_id" in finding:
                valid_ids.add(finding["finding_id"])
                
        for learning in top_learnings.get("top_learnings", []):
            for ref in learning.get("evidence_refs", []):
                self.assertIn(ref, valid_ids)

if __name__ == "__main__":
    unittest.main()

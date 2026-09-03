import os
import shutil
import tempfile
import unittest

from src.analysis.predicates.metadata import MetadataPredicates
from src.repository.scanner import RepositoryScanner


class TestPhase6Metadata(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        
    def tearDown(self):
        shutil.rmtree(self.test_dir)
        
    def _create_file(self, *path_parts):
        full_path = os.path.join(self.test_dir, *path_parts)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        with open(full_path, "w") as f:
            f.write("")
            
    def _create_dir(self, *path_parts):
        full_path = os.path.join(self.test_dir, *path_parts)
        os.makedirs(full_path, exist_ok=True)

    def test_repository_scanner_empty(self):
        scanner = RepositoryScanner(self.test_dir)
        fact = scanner.scan()
        self.assertEqual(len(fact.files_present), 0)
        self.assertEqual(len(fact.directories_present), 0)
        self.assertFalse(fact.has_docker)
        
    def test_repository_scanner_positive(self):
        self._create_file("setup.py")
        self._create_file("Dockerfile")
        self._create_file("main.py")
        self._create_dir("src")
        self._create_dir("tests")
        self._create_file(".github", "workflows", "ci.yml")
        
        scanner = RepositoryScanner(self.test_dir)
        fact = scanner.scan()
        
        self.assertIn("setup.py", fact.files_present)
        self.assertIn("dockerfile", fact.files_present)
        self.assertIn("main.py", fact.files_present)
        self.assertIn("src", fact.directories_present)
        self.assertIn("tests", fact.directories_present)
        self.assertTrue(fact.has_docker)
        self.assertTrue(fact.has_ci)
        
    def test_metadata_predicates(self):
        self._create_file("pyproject.toml")
        self._create_file("docker-compose.yml")
        self._create_dir("k8s")
        
        scanner = RepositoryScanner(self.test_dir)
        fact = scanner.scan()
        
        predicates = MetadataPredicates(fact)
        
        # Positive
        self.assertTrue(predicates.has_packages().matched)
        self.assertTrue(predicates.has_docker().matched)
        self.assertTrue(predicates.has_kubernetes().matched)
        self.assertTrue(predicates.has_deployment_configuration().matched)
        
        # Negative
        self.assertFalse(predicates.has_scripts().matched)
        self.assertFalse(predicates.has_documentation().matched)
        self.assertFalse(predicates.has_ci_cd().matched)
        self.assertFalse(predicates.has_source_directories().matched)

if __name__ == "__main__":
    unittest.main()

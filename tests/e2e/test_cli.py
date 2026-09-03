import os
import shutil
import sys
import tempfile
import unittest
from io import StringIO

from cli import main


class TestCLIE2E(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.output_dir = os.path.join(self.temp_dir, "output")
        
        # Create a minimal target repo
        self.target_dir = os.path.join(self.temp_dir, "target")
        os.makedirs(self.target_dir, exist_ok=True)
        
        with open(os.path.join(self.target_dir, "main.py"), "w") as f:
            f.write("""
import os

class AppRunner:
    def __init__(self, name: str):
        self.name = name
        
    def run(self):
        print(f"Running {self.name}")

def main():
    runner = AppRunner("Demo")
    runner.run()
""")

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_cli_version_command(self):
        saved_stdout = sys.stdout
        try:
            sys.stdout = StringIO()
            with self.assertRaises(SystemExit) as cm:
                main(["version"])
            self.assertEqual(cm.exception.code, 0)
            output = sys.stdout.getvalue()
            self.assertIn("zenith 1.0.0", output)
        finally:
            sys.stdout = saved_stdout

    def test_cli_scan_with_flag(self):
        args = ["scan", self.target_dir, "--output", self.output_dir, "--mode", "fast"]
        main(args)
        
        self.assertTrue(os.path.exists(os.path.join(self.output_dir, "metadata.json")))
        self.assertTrue(os.path.exists(os.path.join(self.output_dir, "knowledge.json")))
        self.assertTrue(os.path.exists(os.path.join(self.output_dir, "top_learnings.json")))

    def test_cli_scan_with_positional_output(self):
        pos_out = os.path.join(self.temp_dir, "pos_output")
        args = ["scan", self.target_dir, pos_out, "--mode", "fast"]
        main(args)
        
        self.assertTrue(os.path.exists(os.path.join(pos_out, "metadata.json")))
        self.assertTrue(os.path.exists(os.path.join(pos_out, "knowledge.json")))
        self.assertTrue(os.path.exists(os.path.join(pos_out, "top_learnings.json")))

if __name__ == "__main__":
    unittest.main()

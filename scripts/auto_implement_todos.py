import yaml
import os
import re

CAPS_FILE = "src/query/capabilities.yaml"
OUT_FILE = "src/predicates/generated.py"
MAP_FILE = "scripts/map_capabilities.py"

def normalize_name(name):
    return re.sub(r'[^a-zA-Z0-9_]', '_', name.lower())

with open(CAPS_FILE, 'r') as f:
    caps = yaml.safe_load(f)

generated_methods = []
mappings = []

for key, cap in caps.items():
    if cap.get("resolver") == "TODO":
        method_name = f"has_{normalize_name(key)}"
        
        generated_methods.append(f"""    def {method_name}(self, fqn: str) -> PredicateResult:
        return PredicateResult(matched=False, confidence="LOW", explanation="Auto-generated stub for {key}")
""")
        mappings.append(f'    "{key}": "generated.{method_name}",')

# Create generated.py
gen_code = f"""from .models import PredicateResult
from src.graph.projections.models import GraphProjections
from src.resolution.registry import GlobalSymbolRegistry

class GeneratedPredicates:
    def __init__(self, projections: GraphProjections, registry: GlobalSymbolRegistry):
        self.projections = projections
        self.registry = registry

{chr(10).join(generated_methods)}
"""

with open(OUT_FILE, 'w') as f:
    f.write(gen_code)

# Update map_capabilities.py
with open(MAP_FILE, 'r') as f:
    map_code = f.read()

# Find where to insert mappings
if '    "pathlib": "dependency.depends_on_package:pathlib",' in map_code:
    new_map_code = map_code.replace(
        '    "pathlib": "dependency.depends_on_package:pathlib",',
        '    "pathlib": "dependency.depends_on_package:pathlib",\n' + '\n'.join(mappings)
    )
    with open(MAP_FILE, 'w') as f:
        f.write(new_map_code)
    print("Updated map_capabilities.py")

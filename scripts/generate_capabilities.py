import re
import yaml
import os

blueprint_path = "/Users/manideepmalyala/.gemini/antigravity-ide/brain/40187bea-83ed-44ef-b5d3-bca342c580f4/PRE_LLM_MASTER_BLUEPRINT.md"
output_path = "/Users/manideepmalyala/Documents/project-z/repo-miner/src/query/capabilities.yaml"

with open(blueprint_path, "r") as f:
    content = f.read()

capabilities = {}
current_category = "General"

# Regex to match numbered items like "1. repository layout"
item_pattern = re.compile(r"^(\d+)\.\s+(.+)$")
header_pattern = re.compile(r"^##?\s+(.+)$")

for line in content.splitlines():
    line = line.strip()
    
    # Track categories
    header_match = header_pattern.match(line)
    if header_match:
        current_category = header_match.group(1).lower().replace(" ", "_")
        continue
        
    # Match items
    item_match = item_pattern.match(line)
    if item_match:
        num = int(item_match.group(1))
        # Skip evidence items (331-340) as per user instruction
        if num >= 331 and num <= 340:
            continue
            
        concept_raw = item_match.group(2)
        concept_key = concept_raw.lower().replace(" ", "_").replace("/", "_").replace("-", "_").replace(".", "_")
        
        # Determine answerability and operation based on category
        answerability = "DIRECT"
        operations = ["LOCATE", "COUNT"]
        resolver_path = "TODO"
        
        if "pattern" in current_category or "solid" in current_category or "design" in current_category:
            answerability = "HEURISTIC"
            operations = ["DETECT", "EXPLAIN"]
            
        if "quality" in current_category or "risk" in current_category:
            answerability = "HEURISTIC"
            operations = ["DETECT", "EXPLAIN"]
            
        capabilities[concept_key] = {
            "concept": concept_key,
            "category": current_category,
            "operations": operations,
            "answerability": answerability,
            "resolver": resolver_path,
            "description": concept_raw
        }

os.makedirs(os.path.dirname(output_path), exist_ok=True)
with open(output_path, "w") as f:
    yaml.dump(capabilities, f, sort_keys=False)

print(f"Generated {len(capabilities)} concepts in {output_path}")

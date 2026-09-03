#!/usr/bin/env python3
import yaml
import json

CAPABILITIES_YAML = "src/query/capabilities.yaml"

def infer_primitives(concept: str, category: str):
    category = category.lower()
    
    # 1. Python Core
    if "syntax" in category or "language_features" in category:
        return {
            "required": ["AST Fact", "Symbol Registration"],
            "ast_available": "Yes (mostly)",
            "graph_available": "No",
            "missing": f"AST extraction for {concept}",
            "recommended": "reusable AST predicate"
        }
        
    # 2. API/Library Intelligence
    if "api_usage" in category or "standard-library" in category or "third-party" in category:
        return {
            "required": ["CallFact", "ImportFact", "FQN Resolution"],
            "ast_available": "Yes",
            "graph_available": "Yes (Calls)",
            "missing": "Targeted FQN matching (e.g. calls_api)",
            "recommended": "generic generic API predicate (calls_api, instantiates_type)"
        }
        
    # 3/4. OOP & Graph Queries
    if "oop" in category or "relations" in category:
        return {
            "required": ["InheritanceFact", "CompositionFact", "Graph Traversal"],
            "ast_available": "Yes",
            "graph_available": "Yes",
            "missing": "Graph query projection",
            "recommended": "graph query predicate (subclasses_of, dependents_of)"
        }
        
    # 5. GoF Patterns
    if "design_patterns" in category:
        return {
            "required": ["OOP Predicates", "Delegation Predicates", "Graph Relationships"],
            "ast_available": "Yes",
            "graph_available": "Yes",
            "missing": "Pattern definitions",
            "recommended": "composite detector of reusable predicates"
        }
        
    # 6. SOLID & Anti-patterns
    if "solid" in category or "anti-pattern" in category or "code_smells" in category:
        return {
            "required": ["Metrics", "Graph Centrality", "Structural Signals"],
            "ast_available": "Yes",
            "graph_available": "Yes",
            "missing": "Risk metrics integration",
            "recommended": "risk detector"
        }
        
    # 7. Architecture
    if "architecture" in category or "network" in category:
        return {
            "required": ["NetworkX Graph", "Centrality Metrics"],
            "ast_available": "Yes",
            "graph_available": "Yes",
            "missing": "Graph algorithm adapter",
            "recommended": "architecture predicate (nx adapter)"
        }
        
    # 8. Repository Metadata
    if "deployment" in category or "infrastructure" in category or "configuration" in category or "ci_cd" in category or "testing_frameworks" in category:
        return {
            "required": ["File Existence", "Regex matches"],
            "ast_available": "No",
            "graph_available": "No",
            "missing": "Non-Python file parser",
            "recommended": "EXTERNAL_METADATA (RepositoryScanner)"
        }
        
    # Default Fallback
    return {
        "required": ["AST Fact"],
        "ast_available": "?",
        "graph_available": "?",
        "missing": "Semantic Analysis",
        "recommended": "predicate"
    }

def build_inventory():
    with open(CAPABILITIES_YAML, 'r') as f:
        capabilities = yaml.safe_load(f)
        
    inventory = []
    
    for concept, cap in capabilities.items():
        resolver = cap.get("resolver", "TODO")
        if not resolver.startswith("generated.") and resolver != "TODO":
            continue
            
        category = cap.get("category", "unknown")
        inferred = infer_primitives(concept, category)
        
        item = {
            "capability": concept,
            "category": category,
            "answerability": cap.get("answerability", "PLACEHOLDER"),
            "current_resolver": resolver,
            "required_evidence": inferred["required"],
            "ast_facts_available": inferred["ast_available"],
            "graph_data_available": inferred["graph_available"],
            "missing_evidence": inferred["missing"],
            "recommended_implementation_type": inferred["recommended"]
        }
        inventory.append(item)
        
    return inventory

if __name__ == "__main__":
    inventory = build_inventory()
    
    # Print out beautifully
    for item in inventory:
        print(f"{item['capability']}")
        print("-" * len(item['capability']))
        print(f"status: {item['answerability']}")
        print(f"category: {item['category']}")
        print(f"resolver: {item['current_resolver']}")
        print("required:")
        for r in item['required_evidence']:
            print(f"  {r}")
        print("missing:")
        print(f"  {item['missing_evidence']}")
        print("implementation:")
        print(f"  {item['recommended_implementation_type']}")
        print()
        
    print(f"\nTotal placeholders found: {len(inventory)}")

    # Write summary group counts
    groups = {}
    for item in inventory:
        g = item['recommended_implementation_type']
        groups[g] = groups.get(g, 0) + 1
        
    print("\nGroup Summary:")
    for g, count in sorted(groups.items(), key=lambda x: x[1], reverse=True):
        print(f"  {count:3}x {g}")

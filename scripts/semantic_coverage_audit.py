import yaml
import json

CAPABILITIES_YAML = "src/query/capabilities.yaml"

def run_audit():
    with open(CAPABILITIES_YAML, 'r') as f:
        capabilities = yaml.safe_load(f)
        
    audit_results = {
        "total": 0,
        "REAL": 0,
        "PARTIAL": 0,
        "HEURISTIC": 0,
        "EXTERNAL_METADATA": 0,
        "PLACEHOLDER": 0,
        "UNSUPPORTED": 0,
        "details": []
    }
    
    for concept, cap in capabilities.items():
        audit_results["total"] += 1
        resolver = cap.get("resolver", "TODO")
        
        status = "UNSUPPORTED"
        if resolver == "TODO":
            status = "UNSUPPORTED"
        elif resolver.startswith("generated."):
            status = "PLACEHOLDER"
        elif resolver.startswith("metadata."):
            status = "EXTERNAL_METADATA"
        elif resolver.startswith("detectors.") or resolver.startswith("patterns.") or resolver.startswith("risks.") or resolver.startswith("architecture."):
            status = "HEURISTIC"
        elif resolver.startswith("dependency.") or resolver.startswith("core.") or resolver.startswith("api.") \
             or resolver.startswith("concurrency.") or resolver.startswith("exceptions.") or resolver.startswith("idioms.") \
             or resolver.startswith("inheritance.") or resolver.startswith("composition.") or resolver.startswith("coupling.") \
             or resolver.startswith("oop."):
            status = "REAL"
        else:
            status = "UNSUPPORTED"
            
        audit_results[status] += 1
        
        audit_results["details"].append({
            "concept": concept,
            "resolver": resolver,
            "status": status,
            "answerability": cap.get("answerability", "UNKNOWN")
        })
        
    return audit_results

if __name__ == "__main__":
    results = run_audit()
    print(f"Total concepts:             {results['total']}")
    print(f"Real implementations:       {results['REAL']}")
    print(f"Heuristic implementations:  {results['HEURISTIC']}")
    print(f"External Metadata:          {results['EXTERNAL_METADATA']}")
    print(f"Placeholder:                {results['PLACEHOLDER']}")
    print(f"Unsupported:                {results['UNSUPPORTED']}")
    print("")
    
    # Save a detailed report to a JSON file for further inspection if needed
    with open("semantic_coverage_report.json", "w") as f:
        json.dump(results, f, indent=2)

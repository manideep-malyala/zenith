import json
import os


def test_evidence_package_contract():
    # Use output from sample repo or run miner here.
    # For now we'll assume the scratch/langchain_out is populated.
    out_dir = "scratch/langchain_out"
    if not os.path.exists(out_dir):
        print("Run python3 scratch/run_miner.py first")
        return
        
    # 1. 3 files must exist
    assert os.path.exists(os.path.join(out_dir, "metadata.json"))
    assert os.path.exists(os.path.join(out_dir, "knowledge.json"))
    assert os.path.exists(os.path.join(out_dir, "top_learnings.json"))
    
    # 2. Legacy files must NOT exist
    assert not os.path.exists(os.path.join(out_dir, "patterns.json"))
    assert not os.path.exists(os.path.join(out_dir, "findings.json"))
    assert not os.path.exists(os.path.join(out_dir, "blueprint.json"))
    assert not os.path.exists(os.path.join(out_dir, "learnings.json"))
    assert not os.path.exists(os.path.join(out_dir, "projections.json"))
    
    # 3. Evidence reference invariant
    with open(os.path.join(out_dir, "knowledge.json")) as f:
        knowledge = json.load(f)
        
    with open(os.path.join(out_dir, "top_learnings.json")) as f:
        learnings_data = json.load(f)
        
    # Map all valid IDs in knowledge
    valid_ids = set()
    # Facts
    for v in knowledge.get("facts", {}).values():
        if isinstance(v, list):
            for fact in v:
                if "fact_id" in fact:
                    valid_ids.add(fact["fact_id"])
    
    # Relationships
    for v in knowledge.get("relationships", {}).values():
        if isinstance(v, list):
            for rel in v:
                if "relationship_id" in rel:
                    valid_ids.add(rel["relationship_id"])
                    
    # Findings
    for finding in knowledge.get("findings", []):
        if "finding_id" in finding:
            valid_ids.add(finding["finding_id"])
            
    # Check that every evidence ref in top_learnings resolves
    for learning in learnings_data.get("top_learnings", []):
        for ref in learning.get("evidence_refs", []):
            assert ref in valid_ids, f"Orphan evidence reference: {ref} in learning {learning['concept_id']}"

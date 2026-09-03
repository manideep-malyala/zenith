import os
import json
import time
import hashlib
from typing import Dict, Any
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.pipeline.orchestrator import ScanPipeline

TARGET_DIR = "/Users/manideepmalyala/Documents/project-z/apm"
CATALOG_DIR = os.path.abspath("src/knowledge/catalog")
OUTPUT_BASE = os.path.abspath("benchmark_outputs")

def get_fingerprint(fact: dict, file_map: dict, category: str) -> str:
    """Create a stable semantic fingerprint for a fact across all categories."""
    components = [category]
    
    # 1. File Path
    if "file_id" in fact:
        components.append(file_map.get(str(fact["file_id"]), str(fact["file_id"])))
    elif "file_path" in fact:
        components.append(fact["file_path"])
        
    # 2. Add all keys except ignored ones
    ignored_keys = {"fact_id", "file_path", "file_id"}
    for k in sorted(fact.keys()):
        if k in ignored_keys:
            continue
        v = fact[k]
        if k == "context" and isinstance(v, dict):
            for ck in sorted(v.keys()):
                components.append(f"ctx_{ck}:{v[ck]}")
        else:
            components.append(f"{k}:{v}")
            
    raw_str = "|".join(str(c) for c in components)
    return hashlib.sha256(raw_str.encode()).hexdigest()


def run_pipeline(name: str, workers: int, mode: str) -> dict:
    output_dir = os.path.join(OUTPUT_BASE, name)
    print(f"\n--- Running: {name} (Workers: {workers}, Mode: {mode}) ---")
    
    pipeline = ScanPipeline(TARGET_DIR, CATALOG_DIR, workers=workers, mode=mode)
    pipeline.run(output_dir)
    
    with open(os.path.join(output_dir, "metadata.json"), "r") as f:
        metadata = json.load(f)
        
    return {
        "name": name,
        "requested_workers": metadata["configuration"]["requested_workers"],
        "actual_workers": metadata["configuration"]["actual_workers"],
        "cpu_count": metadata["configuration"]["cpu_count"],
        "mode": mode,
        "duration": metadata["scan"]["duration_seconds"],
        "fact_extraction": metadata["performance"].get("fact_extraction_seconds", 0),
        "total_facts": metadata["findings_summary"]["total_facts"],
        "knowledge_size": metadata["output"]["knowledge_json_bytes"],
        "output_dir": output_dir
    }

def verify_semantic_regression(baseline_dir: str, optimized_dir: str):
    print("\n--- Running Semantic Regression Check ---")
    
    with open(os.path.join(baseline_dir, "knowledge.json"), "r") as f:
        base_k = json.load(f)
        
    with open(os.path.join(optimized_dir, "knowledge.json"), "r") as f:
        opt_k = json.load(f)
        
    base_file_map = base_k["files"]
    opt_file_map = opt_k["files"]
    
    def get_fingerprints(knowledge_dict, file_map):
        fact_map = {} # fact_id -> fingerprint
        for category, facts in knowledge_dict["facts"].items():
            for f in facts:
                fp = get_fingerprint(f, file_map, category)
                fact_map[f["fact_id"]] = fp
        return fact_map
        
    base_fact_map = get_fingerprints(base_k, base_file_map)
    opt_fact_map = get_fingerprints(opt_k, opt_file_map)
    
    base_fps = set(base_fact_map.values())
    opt_fps = set(opt_fact_map.values())
    
    missing = base_fps - opt_fps
    unexpected = opt_fps - base_fps
    
    print(f"Baseline unique fingerprints: {len(base_fps)}")
    print(f"Optimized unique fingerprints: {len(opt_fps)}")
    print(f"Missing facts: {len(missing)}")
    print(f"Unexpected facts: {len(unexpected)}")
    
    if len(missing) == 0 and len(unexpected) == 0:
        print("✅ Facts are semantically identical.")
    else:
        print("❌ Facts differ semantically.")
        
    print("\n--- Duplication Rate Check (Baseline) ---")
    for category, facts in base_k["facts"].items():
        total = len(facts)
        if total == 0:
            continue
        fps = set(get_fingerprint(f, base_file_map, category) for f in facts)
        unique = len(fps)
        dup_rate = (total - unique) / total * 100
        print(f"{category:20} | Total: {total:<7} | Unique: {unique:<7} | Dup: {dup_rate:.1f}%")
        
    # Compare findings and evidence relationships
    def get_finding_fingerprints(knowledge_dict, fact_map):
        findings_fps = set()
        for f in knowledge_dict["findings"]:
            cid = f["concept_id"]
            evidence_fps = tuple(sorted([fact_map[fid] for fid in f.get("evidence_fact_ids", []) if fid in fact_map]))
            findings_fps.add((cid, evidence_fps))
        return findings_fps
        
    base_finding_fps = get_finding_fingerprints(base_k, base_fact_map)
    opt_finding_fps = get_finding_fingerprints(opt_k, opt_fact_map)
    
    f_missing = base_finding_fps - opt_finding_fps
    f_unexpected = opt_finding_fps - base_finding_fps
    
    print(f"Baseline unique finding structures: {len(base_finding_fps)}")
    print(f"Optimized unique finding structures: {len(opt_finding_fps)}")
    print(f"Missing findings: {len(f_missing)}")
    print(f"Unexpected findings: {len(f_unexpected)}")
    
    if len(f_missing) == 0 and len(f_unexpected) == 0:
        print("✅ Findings and evidence relationships are semantically identical.")
    else:
        print("❌ Findings differ semantically.")

def get_rel_fingerprint(rel: dict) -> tuple:
    """
    Canonical, evidence-ID-free fingerprint for a relationship.

    evidence_fact_ids are excluded because raw fact_ids use uuid4() and are
    non-deterministic across parallel vs single-process runs. The semantic
    identity of a relationship is (type, source, target, status, domain,
    confidence, method).
    """
    return (
        rel.get("relationship_type", ""),
        rel.get("source_fqn", ""),
        rel.get("target_fqn", ""),
        rel.get("resolution_status", ""),
        rel.get("resolution_domain", ""),
        rel.get("confidence", ""),
        rel.get("resolution_method", ""),
    )

def verify_invariant_a(baseline_dir: str, optimized_dir: str):
    """Invariant A: per-type raw fact counts must be identical before and after resolution."""
    print("\n--- Invariant A: Raw Fact Count Immutability ---")
    with open(os.path.join(baseline_dir, "metadata.json")) as f:
        base_meta = json.load(f)
    with open(os.path.join(optimized_dir, "metadata.json")) as f:
        opt_meta = json.load(f)
    base_counts = base_meta["findings_summary"]["fact_counts"]
    opt_counts  = opt_meta["findings_summary"]["fact_counts"]
    all_ok = True
    for fact_type, base_n in base_counts.items():
        opt_n = opt_counts.get(fact_type, -1)
        match = base_n == opt_n
        mark = "✅" if match else "❌"
        print(f"  {mark} {fact_type:22} baseline={base_n:>7}  optimized={opt_n:>7}")
        if not match:
            all_ok = False
    if all_ok:
        print("✅ Invariant A passed: all raw fact counts are identical.")
    else:
        print("❌ Invariant A FAILED: fact counts diverged.")

def verify_invariant_b(baseline_dir: str, optimized_dir: str):
    """Invariant B: canonical relationship sets must be identical between baseline and optimized."""
    print("\n--- Invariant B: Parallel Relationship Determinism ---")
    with open(os.path.join(baseline_dir, "knowledge.json")) as f:
        base_k = json.load(f)
    with open(os.path.join(optimized_dir, "knowledge.json")) as f:
        opt_k = json.load(f)

    all_ok = True
    for rel_type in ("calls", "instantiates", "inherits", "composes"):
        base_fps = {get_rel_fingerprint(r) for r in base_k["relationships"].get(rel_type, [])}
        opt_fps  = {get_rel_fingerprint(r) for r in opt_k["relationships"].get(rel_type, [])}
        missing    = base_fps - opt_fps
        unexpected = opt_fps  - base_fps
        ok = len(missing) == 0 and len(unexpected) == 0
        mark = "✅" if ok else "❌"
        print(f"  {mark} {rel_type:12} base={len(base_fps):>6}  opt={len(opt_fps):>6}  missing={len(missing)}  unexpected={len(unexpected)}")
        if not ok:
            all_ok = False
    if all_ok:
        print("✅ Invariant B passed: relationship sets are semantically identical.")
    else:
        print("❌ Invariant B FAILED: relationship sets diverged between single-process and parallel.")
    
    # Verify deterministic IDs match the expected hash formula
    print("  Checking deterministic relationship_id consistency (baseline)...")
    mismatched_ids = 0
    for rel_type in ("calls", "instantiates", "inherits", "composes"):
        for rel in base_k["relationships"].get(rel_type, []):
            import hashlib
            # Match the formula in graph/models.py: hash(type|source|target)
            type_str = rel.get("relationship_type", "")
            key = "|".join([
                type_str,
                rel.get("source_fqn", ""),
                rel.get("target_fqn", ""),
            ])
            expected_id = hashlib.sha256(key.encode()).hexdigest()
            if rel.get("relationship_id") != expected_id:
                mismatched_ids += 1
    if mismatched_ids == 0:
        print("  ✅ All relationship_ids are deterministic (hash-consistent).")
    else:
        print(f"  ❌ {mismatched_ids} relationship_ids do not match their expected hash.")

def verify_invariant_c(baseline_dir: str):
    """Invariant C: graph must only contain RESOLVED/PARTIAL; AMBIGUOUS/UNRESOLVED stay in knowledge.json only."""
    print("\n--- Invariant C: Graph Conservation ---")
    with open(os.path.join(baseline_dir, "metadata.json")) as f:
        meta = json.load(f)
    with open(os.path.join(baseline_dir, "knowledge.json")) as f:
        k = json.load(f)
    
    graphed  = meta["performance"].get("relationships_graphed", "N/A")
    excluded = meta["performance"].get("relationships_excluded_unresolved", "N/A")
    print(f"  Graphed (RESOLVED+PARTIAL): {graphed}")
    print(f"  Excluded (AMBIGUOUS+UNRESOLVED): {excluded}")
    
    # Count expected graphable from knowledge.json
    graphable_statuses = {"RESOLVED", "PARTIAL"}
    expected_graphed = sum(
        1
        for rel_type in ("calls", "instantiates", "inherits", "composes")
        for rel in k["relationships"].get(rel_type, [])
        if rel.get("resolution_status") in graphable_statuses
    )
    expected_excluded = sum(
        1
        for rel_type in ("calls", "instantiates", "inherits", "composes")
        for rel in k["relationships"].get(rel_type, [])
        if rel.get("resolution_status") not in graphable_statuses
    )
    
    ok_g = (graphed == expected_graphed)
    ok_e = (excluded == expected_excluded)
    print(f"  {'✅' if ok_g else '❌'} Graphed matches expected: {expected_graphed}")
    print(f"  {'✅' if ok_e else '❌'} Excluded matches expected: {expected_excluded}")

    ok = (graphed == expected_graphed) and (excluded == expected_excluded)
    if ok:
        print("✅ Invariant C passed: graph boundary respected.")
    else:
        print("❌ Invariant C FAILED.")

def verify_invariant_d(baseline_dir: str, optimized_dir: str):
    """Invariant D: Projection determinism between single-process and parallel."""
    print("\n--- Invariant D: Projection Determinism ---")
    
    with open(os.path.join(baseline_dir, "projections.json")) as f:
        base_p = json.load(f)
    with open(os.path.join(optimized_dir, "projections.json")) as f:
        opt_p = json.load(f)
        
    all_ok = True
    for proj in ["class_dependencies", "inheritance", "module_coupling"]:
        base_nodes = set(base_p[proj]["nodes"])
        opt_nodes = set(opt_p[proj]["nodes"])
        if base_nodes != opt_nodes:
            print(f"  ❌ {proj} nodes mismatch")
            all_ok = False
            continue
            
        base_edges = base_p[proj]["edges"]
        opt_edges = opt_p[proj]["edges"]
        
        # Serialize edges to comparable strings
        import json as j
        base_edge_set = {j.dumps(e, sort_keys=True) for e in base_edges}
        opt_edge_set = {j.dumps(e, sort_keys=True) for e in opt_edges}
        
        if base_edge_set != opt_edge_set:
            print(f"  ❌ {proj} edges mismatch")
            all_ok = False
            continue
            
        print(f"  ✅ {proj} identical (nodes={len(base_nodes)}, edges={len(base_edges)})")
        
    if all_ok:
        print("✅ Invariant D passed: projections are deterministic.")
    else:
        print("❌ Invariant D FAILED.")

def verify_invariant_e1(baseline_dir: str):
    """Invariant E1: Relationship coverage in projections."""
    print("\n--- Invariant E1: Projection Relationship Coverage ---")
    with open(os.path.join(baseline_dir, "knowledge.json")) as f:
        k = json.load(f)
    with open(os.path.join(baseline_dir, "projections.json")) as f:
        p = json.load(f)
        
    graphable_statuses = {"RESOLVED", "PARTIAL"}
    
    projected_rel_ids = set()
    for proj in ["class_dependencies", "inheritance", "module_coupling"]:
        for edge in p[proj]["edges"]:
            projected_rel_ids.update(edge.get("relationship_ids", []))
            
    invalid_rels = 0
    total_graphed = 0
    for rel_type in ("calls", "instantiates", "inherits", "composes"):
        for rel in k["relationships"].get(rel_type, []):
            if rel.get("resolution_status") in graphable_statuses:
                total_graphed += 1
            elif rel.get("relationship_id") in projected_rel_ids:
                invalid_rels += 1
                
    print(f"  Projected distinct relationship IDs: {len(projected_rel_ids)}")
    print(f"  Total graphable in knowledge.json: {total_graphed}")
    if invalid_rels == 0:
        print("  ✅ All projected relationships have RESOLVED/PARTIAL status.")
        print("✅ Invariant E1 passed: relationship projection boundary respected.")
    else:
        print(f"  ❌ {invalid_rels} UNRESOLVED/AMBIGUOUS relationships leaked into projections.")
        print("❌ Invariant E1 FAILED.")

def check_pattern_findings(baseline_patterns, optimized_patterns):
    print("\n--- Invariant F: Finding Determinism ---")
    if not baseline_patterns and not optimized_patterns:
        print("  ✅ Both baseline and optimized generated 0 pattern findings.")
        return True
        
    def fingerprint_finding(f):
        return f"{f['finding_id']}|{f['detector_id']}|{f['subject_fqn']}"
        
    b_prints = {fingerprint_finding(f) for f in baseline_patterns}
    o_prints = {fingerprint_finding(f) for f in optimized_patterns}
    
    missing = b_prints - o_prints
    unexpected = o_prints - b_prints
    
    if not missing and not unexpected:
        print(f"  ✅ {len(b_prints)} canonical findings are identical.")
        return True
    else:
        print(f"  ❌ Invariant F failed.")
        if missing:
            print(f"     Missing in optimized: {len(missing)}")
        if unexpected:
            print(f"     Unexpected in optimized: {len(unexpected)}")
        return False

def run_pipeline(name: str, workers: int, mode: str) -> dict:
    output_dir = os.path.join(OUTPUT_BASE, name)
    print(f"\n--- Running: {name} (Workers: {workers}, Mode: {mode}) ---")
    
    pipeline = ScanPipeline(TARGET_DIR, CATALOG_DIR, workers=workers, mode=mode)
    pipeline.run(output_dir)
    
    with open(os.path.join(output_dir, "metadata.json"), "r") as f:
        metadata = json.load(f)
    with open(os.path.join(output_dir, "knowledge.json"), "r") as f:
        knowledge = json.load(f)
    with open(os.path.join(output_dir, "projections.json"), "r") as f:
        projections = json.load(f)
    with open(os.path.join(output_dir, "patterns.json"), "r") as f:
        patterns = json.load(f)
        
    return {
        "name": name,
        "mode": mode,
        "requested_workers": workers if workers is not None else "auto",
        "actual_workers": metadata["configuration"]["actual_workers"] if workers is None else (workers or 0),
        "cpu_count": metadata["configuration"]["cpu_count"],
        "duration": metadata["performance"]["total_seconds"],
        "fact_extraction": metadata["performance"]["fact_extraction_seconds"],
        "total_facts": metadata["findings_summary"]["total_facts"],
        "knowledge_size": metadata["output"]["knowledge_json_bytes"],
        "output_dir": output_dir,
        "metadata": metadata,
        "knowledge": knowledge,
        "projections": projections,
        "patterns": patterns
    }


def main():
    if not os.path.exists(TARGET_DIR):
        print(f"Target directory {TARGET_DIR} not found.")
        return
        
    results = []
    
    # 1. Baseline
    results.append(run_pipeline("baseline", 0, "standard"))
    
    # 2. Optimized (auto workers)
    results.append(run_pipeline("optimized", None, "standard"))
    
    # 3. Fast (auto workers)
    results.append(run_pipeline("fast", None, "fast"))
    
    # 4. Deep (auto workers)
    results.append(run_pipeline("deep", None, "deep"))
    
    verify_semantic_regression(
        os.path.join(OUTPUT_BASE, "baseline"),
        os.path.join(OUTPUT_BASE, "optimized")
    )
    
    # --- Three final 6B invariants ---
    verify_invariant_a(os.path.join(OUTPUT_BASE, "baseline"), os.path.join(OUTPUT_BASE, "optimized"))
    verify_invariant_b(os.path.join(OUTPUT_BASE, "baseline"), os.path.join(OUTPUT_BASE, "optimized"))
    verify_invariant_c(os.path.join(OUTPUT_BASE, "baseline"))
    verify_invariant_d(os.path.join(OUTPUT_BASE, "baseline"), os.path.join(OUTPUT_BASE, "optimized"))
    verify_invariant_e1(os.path.join(OUTPUT_BASE, "baseline"))
    
    # Invariant F (Finding Determinism)
    with open(os.path.join(OUTPUT_BASE, "baseline", "patterns.json")) as f:
        baseline_patterns = json.load(f)
    with open(os.path.join(OUTPUT_BASE, "optimized", "patterns.json")) as f:
        optimized_patterns = json.load(f)
    check_pattern_findings(baseline_patterns, optimized_patterns)
    
    # Load relationship counts from metadata for the matrix
    for r in results:
        with open(os.path.join(r["output_dir"], "metadata.json")) as f:
            meta = json.load(f)
        rs = meta.get("resolution_summary", {})
        r["rel_calls"]       = rs.get("calls",       {}).get("total", 0)
        r["rel_instantiates"] = rs.get("instantiates", {}).get("total", 0)
        r["rel_inherits"]    = rs.get("inherits",    {}).get("total", 0)
        r["rel_composes"]    = rs.get("composes",    {}).get("total", 0)

    print("\n--- Final Benchmark Matrix ---")
    print("| Run | Req Workers | Act Workers | CPU | Mode | Duration (s) | Extract (s) | Facts | Size (MB) | CALLS | INST | INHER | COMP |")
    print("|---|---|---|---|---|---|---|---|---|---|---|---|---|")
    for r in results:
        size_mb = r["knowledge_size"] / (1024 * 1024)
        print(f"| {r['name']} | {r['requested_workers']} | {r['actual_workers']} | {r['cpu_count']} | {r['mode']} | {r['duration']} | {r['fact_extraction']} | {r['total_facts']} | {size_mb:.2f} | {r['rel_calls']} | {r['rel_instantiates']} | {r['rel_inherits']} | {r['rel_composes']} |")

if __name__ == "__main__":
    main()

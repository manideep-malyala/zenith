import json
import os


def test_ranking_regression():
    out_dir = "scratch/langchain_out"
    if not os.path.exists(out_dir):
        print("Run python3 scratch/run_miner.py first")
        return
        
    with open(os.path.join(out_dir, "top_learnings.json")) as f:
        learnings_data = json.load(f)
        
    top_learnings = learnings_data.get("top_learnings", [])
    if not top_learnings:
        print("No top learnings generated")
        return
        
    # Test 1: generic AST constructs should not dominate top 10
    top_10 = top_learnings[:10]
    
    # Generic categories that should be filtered out or ranked very low
    generic_categories = [
        "2._complete_python_language_coverage",
        "3._python_standard-library_/_api_usage",
        "1._repository_understanding"
    ]
    
    generic_count = 0
    for learning in top_10:
        if learning.get("category") in generic_categories:
            generic_count += 1
            
    # Assert at most 20% (2 out of 10) are generic structural capabilities
    assert generic_count <= 2, f"Too many generic structural capabilities in top 10: {generic_count}"
    
    # Assert at least some meaningful candidates
    meaningful_count = len(top_10) - generic_count
    assert meaningful_count >= 5, f"Not enough meaningful capabilities in top 10: {meaningful_count}"

def test_frequency_vs_importance():
    # Test Concept A (10k occurrences, low graph/edu) vs Concept B (30 occurrences, high graph/edu)
    from src.output.models import Finding, SourceLocation
    from src.output.top_learnings import TopLearningsBuilder
    
    # Concept A: 10000 occurrences, graph = 0.01, edu = 0.1
    findings_a = []
    for i in range(10000):
        findings_a.append(Finding(
            finding_id=f"fa_{i}",
            capability_id="concept_a",
            category="2._complete_python_language_coverage",
            status="HEURISTIC",
            confidence=1.0,
            evidence_refs=[],
            source_locations=[SourceLocation(file=f"file_{i}.py", line=1)],
            graph_score=0.01,
            educational_value=0.1
        ))
        
    # Concept B: 30 occurrences, graph = 0.9, edu = 0.95
    findings_b = []
    for i in range(30):
        findings_b.append(Finding(
            finding_id=f"fb_{i}",
            capability_id="concept_b",
            category="9._architecture_/_system_structure_(networkx_graph_logic)",
            status="HEURISTIC",
            confidence=0.9,
            evidence_refs=[],
            source_locations=[SourceLocation(file=f"core_file_{i}.py", line=1)],
            graph_score=0.9,
            educational_value=0.95
        ))
        
    capabilities = {
        "concept_a": {"learning_candidate": True, "educational_value": 0.1, "description": "A"},
        "concept_b": {"learning_candidate": True, "educational_value": 0.95, "description": "B"}
    }
    
    graph_metrics = {}
    for i in range(10000):
        graph_metrics[f"file_{i}.py"] = {"pagerank": 0.001, "betweenness_centrality": 0.001}
    for i in range(30):
        graph_metrics[f"core_file_{i}.py"] = {"pagerank": 0.09, "betweenness_centrality": 0.1} # very high graph metrics
        
    builder = TopLearningsBuilder()
    result = builder.build({"name": "test"}, findings_a + findings_b, graph_metrics, capabilities)
    
    learnings = result["top_learnings"]
    assert len(learnings) == 2
    
    # Assert B > A
    assert learnings[0]["concept_id"] == "concept_b"
    assert learnings[1]["concept_id"] == "concept_a"
    
    # B should have a significantly higher score than A despite A having 10,000 occurrences
    assert learnings[0]["importance"] > learnings[1]["importance"] + 0.2

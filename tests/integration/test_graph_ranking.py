def test_graph_ranking_influence():
    # Synthetic graph test to prove graph importance affects ranking
    # Graph A:
    # A → B
    # A → C
    # E → B
    # F → B
    # G → B
    
    # B should be highly central (in-degree 4)
    # D (isolated or low degree) should be low central
    
    from src.output.models import Finding, SourceLocation
    from src.output.top_learnings import TopLearningsBuilder
    
    # Concept X (assigned to B)
    finding_x = Finding(
        finding_id="fx",
        capability_id="concept_x",
        category="9._architecture",
        status="HEURISTIC",
        confidence=0.9,
        evidence_refs=[],
        source_locations=[SourceLocation(file="B.py", line=1)],
        graph_score=0.0,
        educational_value=0.8
    )
    
    # Concept Y (assigned to D)
    finding_y = Finding(
        finding_id="fy",
        capability_id="concept_y",
        category="9._architecture",
        status="HEURISTIC",
        confidence=0.9,
        evidence_refs=[],
        source_locations=[SourceLocation(file="D.py", line=1)],
        graph_score=0.0,
        educational_value=0.8
    )
    
    capabilities = {
        "concept_x": {"learning_candidate": True, "educational_value": 0.8, "description": "X"},
        "concept_y": {"learning_candidate": True, "educational_value": 0.8, "description": "Y"}
    }
    
    # Manually provide graph metrics reflecting the synthetic graph
    graph_metrics = {
        "B.py": {
            "pagerank": 0.1,
            "in_degree_centrality": 0.8,
            "betweenness_centrality": 0.5,
            "core_number": 2,
            "out_degree_centrality": 0.0
        },
        "D.py": {
            "pagerank": 0.01,
            "in_degree_centrality": 0.1,
            "betweenness_centrality": 0.0,
            "core_number": 1,
            "out_degree_centrality": 0.1
        }
    }
    
    builder = TopLearningsBuilder()
    result = builder.build({"name": "test"}, [finding_x, finding_y], graph_metrics, capabilities)
    
    learnings = result["top_learnings"]
    
    assert len(learnings) == 2
    
    # B (concept_x) should be ranked higher than D (concept_y)
    assert learnings[0]["concept_id"] == "concept_x"
    assert learnings[1]["concept_id"] == "concept_y"
    
    # Graph importance of X should be strictly greater than Y
    assert learnings[0]["graph_importance"] > learnings[1]["graph_importance"]
    
    # Total score should be strictly greater
    assert learnings[0]["importance"] > learnings[1]["importance"]

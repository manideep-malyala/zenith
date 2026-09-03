"""Top learnings ranking and evidence package builder.

Applies multi-metric graph scoring, candidate filtering, logarithmic occurrence
dampening, and category diversity capping to generate prioritized architectural insights.
"""

import math
from dataclasses import asdict
from typing import Any

from src.output.models import Finding


class TopLearningsBuilder:
    """Constructs the deterministic top_learnings.json artifact from analysis findings."""

    def __init__(self) -> None:
        """Initializes the TopLearningsBuilder."""

    def build(
        self,
        repository: dict[str, str],
        findings: list[Finding],
        graph_metrics: dict[str, Any],
        capabilities: dict[str, Any],
    ) -> dict[str, Any]:
        """Builds the top_learnings.json schema from a list of UnifiedFindings.

        Args:
            repository: Repository metadata dictionary (e.g. name, commit).
            findings: List of all unified findings emitted across the codebase.
            graph_metrics: Dictionary of computed graph centrality metrics per node.
            capabilities: Catalog mapping of capability concepts and metadata.

        Returns:
            Dict[str, Any]: Formatted top_learnings payload with ranked concepts.
        """
        # Deduplicate and group by capability_id
        grouped: dict[str, list[Finding]] = {}
        for f in findings:
            if f.capability_id not in grouped:
                grouped[f.capability_id] = []
            grouped[f.capability_id].append(f)

        # Build normalized lookup for graph metrics
        def get_file_metrics(filepath: str) -> dict:
            """Looks up graph metrics for a given file path with suffix normalization.

            Args:
                filepath: Target source file path.

            Returns:
                dict: Node metrics dictionary (PageRank, centrality, core number).
            """
            if not filepath:
                return {}
            if filepath in graph_metrics:
                return graph_metrics[filepath]
            for gm_k, gm_v in graph_metrics.items():
                if gm_k.endswith(filepath) or filepath.endswith(gm_k):
                    return gm_v
            return {}

        top_learnings = []
        candidate_count = 0

        for cap_id, cap_findings in grouped.items():
            if not cap_findings:
                continue

            cap = capabilities.get(cap_id, {})
            # Candidate Filtering
            if not cap.get("learning_candidate", False):
                continue

            candidate_count += 1

            # Compute score
            # Score = 0.30 * confidence + 0.30 * graph_importance + 0.20 * educational_value
            #         + 0.15 * evidence_strength + 0.05 * frequency_signal

            occurrences = len(cap_findings)
            # Logarithmic Frequency
            occurrence_signal = min(math.log10(1 + occurrences) / 3.0, 1.0)

            max_confidence = max((f.confidence for f in cap_findings), default=0.0)

            educational_value = float(cap.get("educational_value", 0.5))

            # Evidence strength - heuristic: high if we have specific locations
            evidence_strength = 1.0 if any(f.source_locations for f in cap_findings) else 0.5

            # Graph Score (Calculate normalized score from 5 metrics, top-k average)
            file_scores = []
            seen_files_for_graph = set()
            for f in cap_findings:
                for loc in f.source_locations:
                    if loc.file not in seen_files_for_graph:
                        seen_files_for_graph.add(loc.file)
                        metrics = get_file_metrics(loc.file)

                        pagerank = metrics.get("pagerank", 0.0)
                        betweenness = metrics.get(
                            "betweenness_centrality", metrics.get("betweenness", 0.0)
                        )
                        core_number = metrics.get("core_number", 0.0)
                        in_degree = metrics.get("in_degree_centrality", 0.0)
                        out_degree = metrics.get("out_degree_centrality", 0.0)

                        combined_metric = min(
                            (pagerank * 10)
                            + (betweenness * 5)
                            + (core_number / 10.0)
                            + in_degree
                            + out_degree,
                            1.0,
                        )
                        file_scores.append(combined_metric)

            file_scores.sort(reverse=True)
            top_k = file_scores[:5]
            graph_importance = sum(top_k) / len(top_k) if top_k else 0.0

            score = (
                0.30 * max_confidence
                + 0.30 * graph_importance
                + 0.20 * educational_value
                + 0.15 * evidence_strength
                + 0.05 * occurrence_signal
            )

            # Representative locations
            scored_locations = []
            for f in cap_findings:
                for loc in f.source_locations:
                    metrics = get_file_metrics(loc.file)
                    loc_score = metrics.get("pagerank", 0.0) * 10 + f.confidence
                    file_lower = loc.file.lower()
                    if (
                        "test" in file_lower
                        or "doc" in file_lower
                        or "example" in file_lower
                        or "script" in file_lower
                    ):
                        loc_score -= 1.0  # non-production penalty
                    scored_locations.append((loc_score, loc, f.finding_id))

            scored_locations.sort(key=lambda x: x[0], reverse=True)

            # deduplicate locations by file
            seen_files = set()
            representative_locations = []
            evidence_refs = []

            for _ls, loc, fid in scored_locations:
                if loc.file not in seen_files:
                    seen_files.add(loc.file)
                    representative_locations.append(asdict(loc))
                    evidence_refs.append(fid)
                if len(representative_locations) >= 5:
                    break

            if not evidence_refs:
                evidence_refs = [f.finding_id for f in cap_findings[:5]]

            # Map confidence float to category string
            conf_str = "HIGH" if max_confidence >= 0.8 else "MEDIUM" if max_confidence >= 0.5 else "LOW"

            category_raw = cap.get("category", "patterns")
            category_clean = category_raw.split(".")[-1].replace("_", " ").strip()
            if "risk" in category_clean.lower():
                category_clean = "risks"
            elif "pattern" in category_clean.lower():
                category_clean = "patterns"
            elif "idiom" in category_clean.lower():
                category_clean = "idioms"
            elif "oop" in category_clean.lower():
                category_clean = "oop"
            elif "inheritance" in category_clean.lower():
                category_clean = "inheritance"
            elif "composition" in category_clean.lower():
                category_clean = "composition"
            elif "concurrency" in category_clean.lower():
                category_clean = "concurrency"
            elif "core" in category_clean.lower():
                category_clean = "core"
            else:
                category_clean = "architecture"

            item = {
                "concept_id": cap_id,
                "title": cap.get("description", cap_id.replace("_", " ").title()),
                "category": category_clean,
                "importance": round(score, 3),
                "confidence": conf_str,
                "educational_value": round(educational_value, 2),
                "occurrence_count": occurrences,
                "graph_importance": round(graph_importance, 3),
                "evidence_strength": round(evidence_strength, 2),
                "representative_locations": representative_locations,
                "evidence_refs": evidence_refs,
            }
            top_learnings.append(item)

        # Sort by importance descending
        top_learnings.sort(key=lambda x: x["importance"], reverse=True)

        # Apply Category Diversity Cap (Max 5 per category)
        category_counts: dict[str, int] = {}
        filtered_learnings = []
        for learning in top_learnings:
            cat = learning["category"]
            cnt = category_counts.get(cat, 0)
            if cnt < 5:
                filtered_learnings.append(learning)
                category_counts[cat] = cnt + 1
            if len(filtered_learnings) >= 25:
                break

        # Assign rank 1-indexed
        for rank, learning in enumerate(filtered_learnings, 1):
            learning["rank"] = rank

        return {
            "repository": repository,
            "analysis": {
                "candidate_count": candidate_count,
                "selected_count": len(filtered_learnings),
            },
            "top_learnings": filtered_learnings,
        }

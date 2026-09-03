"""Evidence package serialization writer.

Writes the strict 3-file public Evidence Package (metadata.json,
top_learnings.json, and knowledge.json) using high-performance serialization.
"""

import os

try:
    import orjson

    def _dump_json(data: dict | list, indent: bool = True) -> bytes:
        options = orjson.OPT_INDENT_2 if indent else 0
        return orjson.dumps(data, option=options)

except ImportError:
    import json

    def _dump_json(data: dict | list, indent: bool = True) -> bytes:
        indent_val = 2 if indent else None
        return json.dumps(data, indent=indent_val, separators=(",", ":") if not indent else None).encode("utf-8")


from src.output.models import AnalysisResult
from src.output.top_learnings import TopLearningsBuilder


class EvidencePackageWriter:
    """Serializes pipeline analysis results into the standard 3-file Evidence Package format."""

    def write(self, output_dir: str, analysis: AnalysisResult) -> None:
        """Writes metadata.json, top_learnings.json, and knowledge.json into output_dir.

        Args:
            output_dir: Destination directory path.
            analysis: Unified analysis result object containing metadata, facts,
                relationships, findings, and graph metrics.
        """
        os.makedirs(output_dir, exist_ok=True)

        # 1. Metadata
        with open(os.path.join(output_dir, "metadata.json"), "wb") as f:
            f.write(_dump_json(analysis.metadata, indent=True))

        # 2. Top Learnings
        repo_info = {
            "name": analysis.metadata.get("repository", {}).get("name", "unknown"),
            "commit": analysis.metadata.get("repository", {}).get("commit_sha", "unknown"),
        }
        builder = TopLearningsBuilder()
        top_learnings = builder.build(
            repo_info, analysis.findings, analysis.graph_metrics, analysis.capabilities
        )

        with open(os.path.join(output_dir, "top_learnings.json"), "wb") as f:
            f.write(_dump_json(top_learnings, indent=True))

        # 3. Knowledge Base
        knowledge = {
            "facts": analysis.facts,
            "files": analysis.files,
            "relationships": analysis.relationships,
            "capabilities": analysis.capabilities,
            "findings": [f.to_dict() for f in analysis.findings],
            "graph_metrics": analysis.graph_metrics,
        }

        with open(os.path.join(output_dir, "knowledge.json"), "wb") as f:
            f.write(_dump_json(knowledge, indent=False))

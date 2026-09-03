"""Pipeline context data container.

Maintains mutable and immutable pipeline execution state across all analysis stages.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import networkx as nx

from src.analysis.detectors.registry import DetectorRegistry
from src.analysis.predicates.engine import PredicateEngine
from src.catalog.registry import CapabilityRegistry
from src.graph.projections.models import GraphProjections
from src.output.models import Finding
from src.repository.scanner import MetadataFact
from src.resolution.registry import GlobalSymbolRegistry


@dataclass
class PipelineContext:
    """Encapsulates the state and artifacts produced across pipeline stages."""

    target_dir: Path
    mode: str = "standard"
    workers: int | None = None
    catalog_file: Path | None = None
    output_dir: Path | None = None

    # Registries
    capabilities: CapabilityRegistry = field(default_factory=CapabilityRegistry)
    detector_registry: DetectorRegistry = field(default_factory=DetectorRegistry)
    sym_registry: GlobalSymbolRegistry | None = None
    predicates: PredicateEngine | None = None
    projections: GraphProjections | None = None
    graph: nx.MultiDiGraph | None = None
    repo_metadata: MetadataFact | None = None

    # Discovered & parsed files
    discovered_files: list[Path] = field(default_factory=list)
    file_map: dict[str, str] = field(default_factory=dict)
    metadata_facts: list[Any] = field(default_factory=list)

    # Extracted AST Facts
    all_imports: list[Any] = field(default_factory=list)
    all_calls: list[Any] = field(default_factory=list)
    all_definitions: list[Any] = field(default_factory=list)
    all_inheritances: list[Any] = field(default_factory=list)
    all_assignments: list[Any] = field(default_factory=list)
    all_exceptions: list[Any] = field(default_factory=list)
    all_raises: list[Any] = field(default_factory=list)
    all_lambdas: list[Any] = field(default_factory=list)
    all_decorators: list[Any] = field(default_factory=list)
    all_asyncs: list[Any] = field(default_factory=list)
    all_withs: list[Any] = field(default_factory=list)
    all_loops: list[Any] = field(default_factory=list)
    all_conditionals: list[Any] = field(default_factory=list)
    all_comprehensions: list[Any] = field(default_factory=list)
    all_generators: list[Any] = field(default_factory=list)
    all_returns: list[Any] = field(default_factory=list)

    # Resolved relationships & metrics
    all_relationships: list[Any] = field(default_factory=list)
    all_findings: list[Finding] = field(default_factory=list)
    graph_metrics: dict[str, Any] = field(default_factory=dict)

    # Performance & telemetry
    performance: dict[str, Any] = field(default_factory=dict)
    file_summary: dict[str, Any] = field(default_factory=dict)

"""Master ScanPipeline orchestrator.

Coordinates execution across modular pipeline stages: file discovery,
parallel AST parsing, 3-pass symbol resolution, graph centrality analytics,
semantic pattern detection, and Evidence Package serialization.
"""

import os
import time
from pathlib import Path
from typing import Any

from src.analysis.detectors.patterns.composite import CompositeDetector
from src.analysis.detectors.patterns.dead_code import DeadCodeDetector
from src.analysis.detectors.patterns.dependency_injection import (
    DependencyInjectionDetector,
)
from src.analysis.detectors.patterns.factory import FactoryMethodDetector
from src.analysis.detectors.patterns.singleton import SingletonDetector
from src.analysis.detectors.patterns.srp_risk import SRPRiskDetector
from src.analysis.detectors.patterns.strategy import StrategyDetector
from src.analysis.detectors.registry import DetectorRegistry
from src.catalog.registry import CapabilityRegistry
from src.core.logging import logger
from src.core.parser import PythonParser
from src.output.models import AnalysisResult
from src.output.models import Finding as UnifiedFinding
from src.pipeline.context import PipelineContext
from src.pipeline.stages import (
    ASTExtractionStage,
    DiscoveryStage,
    EvidencePackageWriterStage,
    GraphAnalyticsStage,
    PipelineStage,
    SemanticAnalysisStage,
    SymbolResolutionStage,
)


def _fact_to_dict(fact: Any) -> dict:
    if isinstance(fact, dict):
        return fact
    d = vars(fact).copy()
    if "context" in d:
        ctx = d["context"]
        if ctx is not None and hasattr(ctx, "__dataclass_fields__"):
            d["context"] = {
                "enclosing_function": ctx.enclosing_function,
                "enclosing_class": ctx.enclosing_class,
                "is_async_function": ctx.is_async_function,
                "try_depth": ctx.try_depth,
                "loop_depth": ctx.loop_depth,
                "conditional_depth": ctx.conditional_depth,
                "is_test_context": ctx.is_test_context,
            }
    return d


class ScanPipeline:
    """Master orchestrator executing the 5-phase static analysis pipeline."""

    def __init__(
        self,
        target_dir: str | Path,
        catalog_file: str | Path | None = None,
        catalog_dir: str | Path | None = None,
        workers: int | None = None,
        mode: str = "standard",
    ) -> None:
        """Initializes the ScanPipeline with configuration and detector registry.

        Args:
            target_dir: Root directory of the repository to scan.
            catalog_file: Custom path to capabilities.yaml catalog file.
            catalog_dir: Directory containing capabilities.yaml.
            workers: Number of worker threads for parallel AST parsing.
            mode: Analysis mode ('fast', 'standard', 'deep').
        """
        self.target_dir = os.path.abspath(str(target_dir))

        if catalog_file is None and catalog_dir is not None:
            cat_dir_str = str(catalog_dir)
            if os.path.isdir(cat_dir_str):
                candidate = os.path.join(cat_dir_str, "../capabilities.yaml")
                if os.path.exists(candidate):
                    catalog_file = candidate
                else:
                    catalog_file = os.path.join(
                        os.path.dirname(__file__), "../catalog/capabilities.yaml"
                    )
            else:
                catalog_file = cat_dir_str

        if catalog_file is None:
            catalog_file = os.path.join(
                os.path.dirname(__file__), "../catalog/capabilities.yaml"
            )

        self.catalog_file = os.path.abspath(str(catalog_file))
        self.parser = PythonParser()

        self.requested_workers = workers if workers is not None else "auto"
        self.workers = workers if workers is not None else min(os.cpu_count() or 4, 8)
        self.mode = mode

        # Detector Registry
        self.detector_registry = DetectorRegistry()
        self.detector_registry.register(CompositeDetector())
        self.detector_registry.register(StrategyDetector())
        self.detector_registry.register(DependencyInjectionDetector())
        self.detector_registry.register(SRPRiskDetector())
        self.detector_registry.register(SingletonDetector())
        self.detector_registry.register(FactoryMethodDetector())
        self.detector_registry.register(DeadCodeDetector())

        # Capability Registry
        self.capabilities = CapabilityRegistry()
        self.capabilities.load_from_yaml(self.catalog_file)

        # Pipeline outputs & state (preserved for backward-compatibility)
        self.all_imports: list[Any] = []
        self.all_calls: list[Any] = []
        self.all_definitions: list[Any] = []
        self.all_inheritances: list[Any] = []
        self.all_assignments: list[Any] = []
        self.all_exceptions: list[Any] = []
        self.all_raises: list[Any] = []
        self.all_lambdas: list[Any] = []
        self.all_decorators: list[Any] = []
        self.all_asyncs: list[Any] = []
        self.all_withs: list[Any] = []
        self.all_loops: list[Any] = []
        self.all_conditionals: list[Any] = []
        self.all_comprehensions: list[Any] = []
        self.all_generators: list[Any] = []
        self.all_returns: list[Any] = []
        self.all_relationships: list[Any] = []
        self.all_findings: list[UnifiedFinding] = []
        self.pattern_findings: list[Any] = []

        self.files_discovered = 0
        self.files_parsed = 0
        self.parse_errors = 0
        self.performance: dict[str, Any] = {}
        self.file_summary: dict[str, Any] = {}
        self.file_map: dict[str, str] = {}
        self.graph_metrics: dict[str, Any] = {}

        self.sym_registry = None
        self.predicates = None
        self.projections = None
        self.graph = None

    def default_stages(self) -> list[PipelineStage]:
        """Constructs the default execution stages for the pipeline.

        Returns:
            List[PipelineStage]: Ordered list of scan stages.
        """
        return [
            DiscoveryStage(),
            ASTExtractionStage(),
            SymbolResolutionStage(),
            GraphAnalyticsStage(),
            SemanticAnalysisStage(),
            EvidencePackageWriterStage(),
        ]

    def run(
        self,
        output_dir: str | Path | None = None,
        stages: list[PipelineStage] | None = None,
    ) -> AnalysisResult:
        """Executes the pipeline stages and produces an AnalysisResult.

        Args:
            output_dir: Optional destination directory to write Evidence Package files.
            stages: Optional custom list of PipelineStage instances to run.

        Returns:
            AnalysisResult: Aggregated metadata, facts, relationships, and findings.
        """
        t0 = time.time()
        out_path = Path(output_dir) if output_dir else None

        ctx = PipelineContext(
            target_dir=Path(self.target_dir),
            mode=self.mode,
            workers=self.workers,
            catalog_file=Path(self.catalog_file),
            output_dir=out_path,
            capabilities=self.capabilities,
            detector_registry=self.detector_registry,
        )

        pipeline_stages = stages if stages is not None else self.default_stages()

        for stage in pipeline_stages:
            stage_start = time.time()
            stage.execute(ctx)
            stage_elapsed = time.time() - stage_start
            logger.debug(f"Stage '{stage.name()}' completed in {stage_elapsed:.3f}s")

        ctx.performance["total_seconds"] = round(time.time() - t0, 3)

        # Sync context back to self for complete backward-compatibility
        self.all_imports = ctx.all_imports
        self.all_calls = ctx.all_calls
        self.all_definitions = ctx.all_definitions
        self.all_inheritances = ctx.all_inheritances
        self.all_assignments = ctx.all_assignments
        self.all_exceptions = ctx.all_exceptions
        self.all_raises = ctx.all_raises
        self.all_lambdas = ctx.all_lambdas
        self.all_decorators = ctx.all_decorators
        self.all_asyncs = ctx.all_asyncs
        self.all_withs = ctx.all_withs
        self.all_loops = ctx.all_loops
        self.all_conditionals = ctx.all_conditionals
        self.all_comprehensions = ctx.all_comprehensions
        self.all_generators = ctx.all_generators
        self.all_returns = ctx.all_returns
        self.all_relationships = ctx.all_relationships
        self.all_findings = ctx.all_findings
        self.performance = ctx.performance
        self.file_summary = ctx.file_summary
        self.file_map = ctx.file_map
        self.graph_metrics = ctx.graph_metrics
        self.sym_registry = ctx.sym_registry
        self.predicates = ctx.predicates
        self.projections = ctx.projections
        self.graph = ctx.graph

        self.files_discovered = ctx.file_summary.get("python_files_found", 0)
        self.files_parsed = ctx.file_summary.get("python_files_parsed_successfully", 0)
        self.parse_errors = ctx.file_summary.get("python_files_with_parse_errors", 0)

        # Return AnalysisResult
        git_meta_dict = {
            "name": getattr(ctx.repo_metadata, "name", "unknown") if ctx.repo_metadata else "unknown",
            "commit_sha": getattr(ctx.repo_metadata, "commit_sha", "unknown") if ctx.repo_metadata else "unknown",
            "branch": getattr(ctx.repo_metadata, "branch", "unknown") if ctx.repo_metadata else "unknown",
            "origin_url": getattr(ctx.repo_metadata, "origin_url", "") if ctx.repo_metadata else "",
        }

        metadata_payload = {
            "repository": git_meta_dict,
            "scan_environment": {
                "python_version": f"{os.sys.version_info.major}.{os.sys.version_info.minor}.{os.sys.version_info.micro}",
                "timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "platform": os.uname().sysname if hasattr(os, "uname") else "Unknown",
            },
            "file_summary": ctx.file_summary,
            "performance": ctx.performance,
        }

        facts_payload = {
            "definitions": [_fact_to_dict(f) for f in ctx.all_definitions],
            "calls": [_fact_to_dict(f) for f in ctx.all_calls],
            "imports": [_fact_to_dict(f) for f in ctx.all_imports],
            "inheritances": [_fact_to_dict(f) for f in ctx.all_inheritances],
            "assignments": [_fact_to_dict(f) for f in ctx.all_assignments],
            "exceptions": [_fact_to_dict(f) for f in ctx.all_exceptions],
            "raises": [_fact_to_dict(f) for f in ctx.all_raises],
            "lambdas": [_fact_to_dict(f) for f in ctx.all_lambdas],
            "decorators": [_fact_to_dict(f) for f in ctx.all_decorators],
            "asyncs": [_fact_to_dict(f) for f in ctx.all_asyncs],
            "withs": [_fact_to_dict(f) for f in ctx.all_withs],
            "loops": [_fact_to_dict(f) for f in ctx.all_loops],
            "conditionals": [_fact_to_dict(f) for f in ctx.all_conditionals],
            "comprehensions": [_fact_to_dict(f) for f in ctx.all_comprehensions],
            "generators": [_fact_to_dict(f) for f in ctx.all_generators],
            "returns": [_fact_to_dict(f) for f in ctx.all_returns],
        }

        relationships_payload = {
            "resolved": [vars(r) for r in ctx.all_relationships],
        }

        capabilities_dict = {
            cap.concept: {
                "category": getattr(cap, "category", "general"),
                "operations": [op.value for op in cap.operations],
                "answerability": cap.answerability.value,
                "resolver": cap.resolver_path,
                "description": cap.description,
                "learning_candidate": cap.learning_candidate,
                "educational_value": cap.educational_value,
            }
            for cap in ctx.capabilities.get_all()
        }

        return AnalysisResult(
            metadata=metadata_payload,
            facts=facts_payload,
            files=ctx.file_map,
            relationships=relationships_payload,
            capabilities=capabilities_dict,
            findings=ctx.all_findings,
            graph_metrics=ctx.graph_metrics,
        )

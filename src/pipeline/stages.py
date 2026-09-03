"""Modular pipeline stage definitions.

Each stage implements the PipelineStage protocol, consuming and updating
the shared PipelineContext in an isolated, measurable unit of work.
"""

import concurrent.futures
import os
import time
from pathlib import Path
from typing import Any, Protocol

from src.analysis.analyzers import AnalysisContext, DetectionAnalyzer, PredicateAnalyzer
from src.analysis.detectors.engine import DetectionEngine
from src.analysis.predicates.engine import PredicateEngine
from src.core.extractor import FactExtractor
from src.core.logging import logger
from src.core.parser import PythonParser
from src.graph.analytics import GraphAnalytics
from src.graph.builder import GraphBuilder
from src.graph.projections.builder import ProjectionBuilder
from src.output.models import AnalysisResult
from src.output.models import Finding as UnifiedFinding
from src.output.writer import EvidencePackageWriter
from src.pipeline.context import PipelineContext
from src.repository.discovery import discover_python_files
from src.repository.git import get_git_metadata
from src.repository.scanner import RepositoryScanner
from src.resolution.registry import GlobalSymbolRegistry
from src.resolution.relationship_resolver import RelationshipResolver
from src.resolution.symbol_resolver import ScopeResolver


def _parse_and_extract_file(file_path_str: str) -> dict[str, Any]:
    """Helper for parallel AST parsing and fact extraction.

    Args:
        file_path_str: String path to the target Python file.

    Returns:
        dict[str, Any]: Dictionary containing all extracted AST facts.
    """
    parser = PythonParser()
    extractor = FactExtractor(file_path_str)
    tree = parser.parse_file(file_path_str)

    if tree is None:
        return {
            "status": "error",
            "file": file_path_str,
            "imports": [],
            "calls": [],
            "definitions": [],
            "inheritances": [],
            "assignments": [],
            "exceptions": [],
            "raises": [],
            "lambdas": [],
            "decorators": [],
            "asyncs": [],
            "withs": [],
            "loops": [],
            "conditionals": [],
            "comprehensions": [],
            "generators": [],
            "returns": [],
        }

    extracted = extractor.extract(tree)
    return {
        "status": "success",
        "file": file_path_str,
        "imports": extracted.get("imports", []),
        "calls": extracted.get("calls", []),
        "definitions": extracted.get("definitions", []),
        "inheritances": extracted.get("inheritances", []),
        "assignments": extracted.get("assignments", []),
        "exceptions": extracted.get("exceptions", []),
        "raises": extracted.get("raises", []),
        "lambdas": extracted.get("lambdas", []),
        "decorators": extracted.get("decorators", []),
        "asyncs": extracted.get("asyncs", []),
        "withs": extracted.get("withs", []),
        "loops": extracted.get("loops", []),
        "conditionals": extracted.get("conditionals", []),
        "comprehensions": extracted.get("comprehensions", []),
        "generators": extracted.get("generators", []),
        "returns": extracted.get("returns", []),
    }


class PipelineStage(Protocol):
    """Interface for all scan pipeline execution stages."""

    def name(self) -> str:
        """Returns the human-readable name of the stage."""
        ...

    def execute(self, ctx: PipelineContext) -> None:
        """Executes stage logic and mutates the PipelineContext in place.

        Args:
            ctx: Shared pipeline context container.
        """
        ...


class DiscoveryStage:
    """Discovers source files and scans repository metadata."""

    def name(self) -> str:
        return "discovery"

    def execute(self, ctx: PipelineContext) -> None:
        t0 = time.time()
        target_str = str(ctx.target_dir)

        discovery_result = discover_python_files(target_str)
        ctx.discovered_files = [Path(p) for p in discovery_result.scanned_files]

        scanner = RepositoryScanner(target_str)
        metadata_fact = scanner.scan()
        ctx.metadata_facts = [metadata_fact]
        ctx.repo_metadata = metadata_fact

        ctx.file_map = {}
        for file_path in discovery_result.scanned_files:
            try:
                ctx.file_map[file_path] = os.path.relpath(file_path, target_str)
            except ValueError:
                ctx.file_map[file_path] = file_path

        ctx.file_summary = {
            "total_files": discovery_result.total_files,
            "python_files_found": discovery_result.python_files_found,
            "non_python_files": discovery_result.non_python_files,
            "python_files_scanned": discovery_result.python_files_scanned,
            "python_files_excluded": discovery_result.python_files_excluded,
            "python_files_parsed_successfully": 0,
            "python_files_with_parse_errors": 0,
        }

        ctx.performance["discovery_seconds"] = round(time.time() - t0, 3)
        logger.debug(f"Discovered {len(ctx.discovered_files)} Python files in {ctx.performance['discovery_seconds']}s")


class ASTExtractionStage:
    """Parses ASTs and extracts structural language facts in parallel."""

    def name(self) -> str:
        return "ast_extraction"

    def execute(self, ctx: PipelineContext) -> None:
        t0 = time.time()
        files = [str(f) for f in ctx.discovered_files]

        if not files:
            ctx.performance["fact_extraction_seconds"] = 0.0
            return

        workers = ctx.workers if ctx.workers is not None else min(32, (os.cpu_count() or 1) + 4)
        if workers <= 0:
            workers = None

        successful_parses = 0
        error_parses = 0

        with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
            futures = [executor.submit(_parse_and_extract_file, f) for f in files]
            for future in concurrent.futures.as_completed(futures):
                res = future.result()
                if res["status"] == "success":
                    successful_parses += 1
                else:
                    error_parses += 1

                ctx.all_imports.extend(res["imports"])
                ctx.all_calls.extend(res["calls"])
                ctx.all_definitions.extend(res["definitions"])
                ctx.all_inheritances.extend(res["inheritances"])
                ctx.all_assignments.extend(res["assignments"])
                ctx.all_exceptions.extend(res["exceptions"])
                ctx.all_raises.extend(res["raises"])
                ctx.all_lambdas.extend(res["lambdas"])
                ctx.all_decorators.extend(res["decorators"])
                ctx.all_asyncs.extend(res["asyncs"])
                ctx.all_withs.extend(res["withs"])
                ctx.all_loops.extend(res["loops"])
                ctx.all_conditionals.extend(res["conditionals"])
                ctx.all_comprehensions.extend(res["comprehensions"])
                ctx.all_generators.extend(res["generators"])
                ctx.all_returns.extend(res["returns"])

        ctx.file_summary["python_files_parsed_successfully"] = successful_parses
        ctx.file_summary["python_files_with_parse_errors"] = error_parses
        ctx.performance["fact_extraction_seconds"] = round(time.time() - t0, 3)
        ctx.performance["parsing_seconds"] = ctx.performance["fact_extraction_seconds"]
        logger.debug(f"Extracted AST facts across {successful_parses} files in {ctx.performance['fact_extraction_seconds']}s")


class SymbolResolutionStage:
    """Performs 3-pass global symbol registry and typed relationship resolution."""

    def name(self) -> str:
        return "symbol_resolution"

    def execute(self, ctx: PipelineContext) -> None:
        t0 = time.time()
        target_str = str(ctx.target_dir)

        # Pass 1: Global symbol registry
        ctx.sym_registry = GlobalSymbolRegistry(project_root=target_str)
        ctx.sym_registry.build(ctx.all_definitions)

        # Pass 2: Per-file scope mapping
        imports_by_file: dict[str, list[Any]] = {}
        for imp in ctx.all_imports:
            imports_by_file.setdefault(imp.file_path, []).append(imp)

        scope_resolvers = {
            file_path: ScopeResolver(file_imports, ctx.sym_registry, file_path)
            for file_path, file_imports in imports_by_file.items()
        }

        # Pass 3: Typed edge linking
        rel_resolver = RelationshipResolver(ctx.sym_registry, scope_resolvers)
        ctx.all_relationships = rel_resolver.resolve_all(
            calls=ctx.all_calls,
            inheritances=ctx.all_inheritances,
            assignments=ctx.all_assignments,
        )

        ctx.performance["resolution_seconds"] = round(time.time() - t0, 3)
        logger.debug(f"Resolved {len(ctx.all_relationships)} relationships in {ctx.performance['resolution_seconds']}s")


class GraphAnalyticsStage:
    """Builds the MultiDiGraph and calculates the 5 NetworkX centrality algorithms."""

    def name(self) -> str:
        return "graph_analytics"

    def execute(self, ctx: PipelineContext) -> None:
        t0 = time.time()

        graph_builder = GraphBuilder()
        graph_builder.build_from_facts(ctx.all_imports, ctx.all_definitions, ctx.all_calls)
        graphed, excluded = graph_builder.build_from_relationships(ctx.all_relationships)
        ctx.performance["relationships_graphed"] = graphed
        ctx.performance["relationships_excluded_unresolved"] = excluded

        ctx.graph = graph_builder.networkx_graph

        # Projections
        proj_builder = ProjectionBuilder()
        all_semantic_facts = (
            ctx.all_exceptions
            + ctx.all_raises
            + ctx.all_lambdas
            + ctx.all_decorators
            + ctx.all_asyncs
            + ctx.all_withs
            + ctx.all_loops
            + ctx.all_conditionals
            + ctx.all_comprehensions
            + ctx.all_generators
            + ctx.all_assignments
            + ctx.all_imports
            + ctx.all_definitions
            + ctx.all_calls
            + ctx.all_returns
        )
        assert ctx.sym_registry is not None
        ctx.projections = proj_builder.build(
            ctx.all_relationships, ctx.sym_registry, all_facts=all_semantic_facts
        )

        # Graph Centrality Analytics
        import_projection = graph_builder.get_file_import_projection()
        analytics = GraphAnalytics(import_projection)
        ctx.graph_metrics = analytics.generate_report(mode=ctx.mode)
        ctx.performance.update(analytics.performance)

        ctx.performance["graph_construction_seconds"] = round(time.time() - t0, 3)
        logger.debug(f"Computed graph centrality analytics in {ctx.performance['graph_construction_seconds']}s")


class SemanticAnalysisStage:
    """Executes the PredicateEngine (285 heuristics) and GoF/Risk Pattern Detectors."""

    def name(self) -> str:
        return "semantic_analysis"

    def execute(self, ctx: PipelineContext) -> None:
        t0 = time.time()
        assert ctx.projections is not None
        assert ctx.sym_registry is not None

        ctx.predicates = PredicateEngine(
            ctx.projections,
            ctx.sym_registry,
            metadata_facts=ctx.metadata_facts,
            graph_metrics=ctx.graph_metrics,
            graph=ctx.graph,
            repo_metadata=ctx.repo_metadata,
        )

        det_engine = DetectionEngine(ctx.detector_registry)

        all_semantic_facts = (
            ctx.all_exceptions
            + ctx.all_raises
            + ctx.all_lambdas
            + ctx.all_decorators
            + ctx.all_asyncs
            + ctx.all_withs
            + ctx.all_loops
            + ctx.all_conditionals
            + ctx.all_comprehensions
            + ctx.all_generators
            + ctx.all_assignments
            + ctx.all_imports
            + ctx.all_definitions
            + ctx.all_calls
            + ctx.all_returns
        )

        analysis_context = AnalysisContext(
            projections=ctx.projections,
            sym_registry=ctx.sym_registry,
            metadata_facts=ctx.metadata_facts,
            graph_metrics=ctx.graph_metrics,
            graph=ctx.graph,
            repo_metadata=ctx.repo_metadata,
            all_relationships=ctx.all_relationships,
            all_facts=all_semantic_facts,
            all_calls=ctx.all_calls,
            file_map=ctx.file_map,
            capabilities=ctx.capabilities,
            predicates=ctx.predicates,
        )

        analyzers = [
            PredicateAnalyzer(ctx.predicates),
            DetectionAnalyzer(det_engine),
        ]

        all_unified_findings: list[UnifiedFinding] = []
        for analyzer in analyzers:
            all_unified_findings.extend(analyzer.analyze(analysis_context))

        ctx.all_findings = all_unified_findings
        ctx.performance["analysis_seconds"] = round(time.time() - t0, 3)
        logger.debug(f"Generated {len(ctx.all_findings)} semantic findings in {ctx.performance['analysis_seconds']}s")


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


class EvidencePackageWriterStage:
    """Builds and serializes the 3-file Evidence Package (metadata, knowledge, top_learnings)."""

    def name(self) -> str:
        return "evidence_writer"

    def execute(self, ctx: PipelineContext) -> None:
        if not ctx.output_dir:
            return

        t0 = time.time()
        output_str = str(ctx.output_dir)
        os.makedirs(output_str, exist_ok=True)

        git_meta = get_git_metadata(str(ctx.target_dir))
        repo_name = os.path.basename(os.path.abspath(str(ctx.target_dir)))
        metadata_payload = {
            "repository": {
                "name": repo_name,
                "commit_sha": git_meta.commit_sha or "unknown",
                "branch": git_meta.branch or "unknown",
                "origin_url": git_meta.url or "",
            },
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

        result = AnalysisResult(
            metadata=metadata_payload,
            facts=facts_payload,
            files=ctx.file_map,
            relationships=relationships_payload,
            capabilities=capabilities_dict,
            findings=ctx.all_findings,
            graph_metrics=ctx.graph_metrics,
        )

        writer = EvidencePackageWriter()
        writer.write(output_str, result)
        ctx.performance["writing_seconds"] = round(time.time() - t0, 3)
        logger.debug(f"Serialized Evidence Package to {output_str} in {ctx.performance['writing_seconds']}s")

import hashlib
import inspect
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import Any, Protocol

from src.analysis.detectors.engine import DetectionEngine
from src.analysis.predicates.engine import PredicateEngine
from src.catalog.registry import CapabilityRegistry
from src.output.models import Finding, SourceLocation


@dataclass
class AnalysisContext:
    projections: Any
    sym_registry: Any
    metadata_facts: Any
    graph_metrics: dict
    graph: Any
    repo_metadata: Any
    all_relationships: list[Any]
    all_facts: list[Any]
    all_calls: list[Any]
    file_map: dict
    capabilities: CapabilityRegistry
    predicates: PredicateEngine


class Analyzer(Protocol):
    def analyze(self, context: AnalysisContext) -> list[Finding]:
        ...


class PredicateAnalyzer:
    """Evaluates catalog capabilities concurrently with fast pre-filtering."""

    def __init__(self, engine: PredicateEngine, workers: int = 8) -> None:
        self.engine = engine
        self.workers = workers

    def _eval_capability(self, cap: Any, context: AnalysisContext) -> list[Finding]:
        findings: list[Finding] = []
        if cap.resolver_path.startswith("detectors.") or cap.resolver_path == "TODO":
            return findings

        parts = cap.resolver_path.split(":")
        path = parts[0]
        args = parts[1:] if len(parts) > 1 else []

        try:
            group, method_name = path.split(".")
            predicate_group = getattr(self.engine, group)
            method = getattr(predicate_group, method_name)
        except (ValueError, AttributeError):
            return findings

        # Check if this is a metadata/repo-level predicate (takes no required FQN parameter)
        try:
            sig = inspect.signature(method)
            required_params = [
                p
                for p in sig.parameters.values()
                if p.default is inspect.Parameter.empty
                and p.kind in (inspect.Parameter.POSITIONAL_ONLY, inspect.Parameter.POSITIONAL_OR_KEYWORD)
            ]
        except (ValueError, TypeError):
            required_params = []

        # Repo/Metadata-level execution (0 positional params or group == 'metadata')
        if group == "metadata" or len(required_params) == 0:
            try:
                res = method(*args) if args else method()
                if res.matched:
                    hash_input = f"{cap.concept}|{group}"
                    fid = hashlib.sha256(hash_input.encode("utf-8")).hexdigest()
                    findings.append(
                        Finding(
                            finding_id=fid,
                            capability_id=cap.concept,
                            category=group,
                            status="HEURISTIC",
                            confidence=1.0,
                            evidence_refs=[],
                            source_locations=[],
                            graph_score=0.0,
                            educational_value=float(cap.educational_value)
                            if hasattr(cap, "educational_value")
                            else 0.5,
                            explanation=getattr(res, "explanation", "") or "",
                        )
                    )
            except Exception:
                pass
            return findings

        # Symbol-level predicate: Smart pre-filtering by domain
        if group in ("oop", "inheritance", "composition") or "class" in method_name:
            candidates = context.sym_registry.definitions_by_type.get("class", [])
        elif group in ("concurrency", "exceptions") or method_name.startswith("is_async") or method_name.startswith("is_generator"):
            candidates = (
                context.sym_registry.definitions_by_type.get("function", [])
                + context.sym_registry.definitions_by_type.get("method", [])
                + context.sym_registry.definitions_by_type.get("async_function", [])
                + context.sym_registry.definitions_by_type.get("async_method", [])
            )
        else:
            candidates = (
                context.sym_registry.definitions_by_type.get("class", [])
                + context.sym_registry.definitions_by_type.get("function", [])
                + context.sym_registry.definitions_by_type.get("method", [])
                + context.sym_registry.definitions_by_type.get("async_function", [])
                + context.sym_registry.definitions_by_type.get("async_method", [])
            )

        for fqn, defn in candidates:
            try:
                res = method(fqn, *args) if args else method(fqn)
                if res.matched:
                    hash_input = f"{cap.concept}|{fqn}"
                    fid = hashlib.sha256(hash_input.encode("utf-8")).hexdigest()
                    locs = []
                    if defn.file_path:
                        rel = context.file_map.get(defn.file_path, defn.file_path)
                        locs.append(SourceLocation(file=rel, line=defn.start_line))

                    graph_score = 0.0
                    if defn.file_path in context.graph_metrics:
                        graph_score = context.graph_metrics[defn.file_path].get("pagerank", 0.0)

                    findings.append(
                        Finding(
                            finding_id=fid,
                            capability_id=cap.concept,
                            category=group,
                            status="HIGH",
                            confidence=1.0,
                            evidence_refs=list(getattr(res, "evidence_fact_ids", [])) or [],
                            source_locations=locs,
                            graph_score=graph_score,
                            educational_value=float(cap.educational_value)
                            if hasattr(cap, "educational_value")
                            else 0.5,
                            explanation=getattr(res, "explanation", "") or "",
                        )
                    )
            except Exception:
                continue

        return findings

    def analyze(self, context: AnalysisContext) -> list[Finding]:
        all_caps = context.capabilities.get_all()
        findings: list[Finding] = []

        with ThreadPoolExecutor(max_workers=self.workers) as executor:
            futures = [executor.submit(self._eval_capability, cap, context) for cap in all_caps]
            for f in futures:
                findings.extend(f.result())

        return findings


class DetectionAnalyzer:
    """Executes the GoF & Architectural Risk detection engine."""

    def __init__(self, engine: DetectionEngine) -> None:
        self.engine = engine

    def analyze(self, context: AnalysisContext) -> list[Finding]:
        findings: list[Finding] = []
        raw_findings = self.engine.run(
            predicates=context.predicates,
            symbol_registry=context.sym_registry,
            relationships=context.all_relationships,
        )

        for rf in raw_findings:
            locs = []
            defn = context.sym_registry.definitions_by_fqn.get(rf.subject_fqn)
            if defn and defn.file_path:
                rel = context.file_map.get(defn.file_path, defn.file_path)
                locs.append(SourceLocation(file=rel, line=defn.start_line))

            graph_score = 0.0
            if defn and defn.file_path in context.graph_metrics:
                graph_score = context.graph_metrics[defn.file_path].get("pagerank", 0.0)

            findings.append(
                Finding(
                    finding_id=rf.finding_id,
                    capability_id=rf.detector_id,
                    category=rf.category,
                    status=rf.finding_type,
                    confidence=1.0,
                    evidence_refs=list(rf.evidence_relationship_ids),
                    source_locations=locs,
                    graph_score=graph_score,
                    educational_value=0.95,
                    explanation=rf.explanation,
                )
            )

        return findings

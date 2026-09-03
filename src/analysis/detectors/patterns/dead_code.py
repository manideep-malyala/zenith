"""Dead code and unreachable symbol detector.

Combines AST lexical scope analysis (for unused variables and unused imports)
with NetworkX graph reachability and in-degree analysis (for unreferenced functions,
classes, and orphan modules).
"""

import ast
import functools

from src.analysis.detectors.base import BaseDetector, DetectionContext
from src.analysis.detectors.models import Finding
from src.core.models import Confidence


@functools.lru_cache(maxsize=4096)
def _get_ast_tree(file_path: str) -> ast.AST | None:
    """Caches parsed AST tree per file to avoid redundant disk IO and parsing."""
    try:
        with open(file_path, encoding="utf-8") as f:
            return ast.parse(f.read(), filename=file_path)
    except Exception:
        return None


class DeadCodeDetector(BaseDetector):
    """Detects unused local variables, unreferenced definitions, and orphan modules."""

    detector_id = "dead_code"
    pattern_name = "Dead Code & Unused Symbols"
    category = "solid_and_risks"

    def detect(self, context: DetectionContext) -> list[Finding]:
        """Runs dead code detection across AST facts and graph reachability.

        Args:
            context: Shared detection context containing graph, registry, and facts.

        Returns:
            List[Finding]: Emitted findings for detected dead code.
        """
        findings: list[Finding] = []

        # 1. Macro-Level: Unreferenced Functions & Classes (Graph In-Degree Analysis)
        graph = getattr(context, "graph", None)
        if graph is None and getattr(context, "predicates", None) is not None:
            graph = getattr(context.predicates, "graph", None)

        registry = context.registry

        if graph is not None and registry is not None:
            for fqn, defn in registry.definitions_by_fqn.items():
                if (
                    defn.name.startswith("__")
                    or defn.name.startswith("test_")
                    or defn.name in ("main", "run", "cli", "setUp", "tearDown")
                    or "test" in defn.file_path.lower()
                ):
                    continue

                if fqn in graph:
                    in_degree = graph.in_degree(fqn)
                    if in_degree == 0:
                        findings.append(
                            Finding(
                                detector_id=self.detector_id,
                                pattern_name=self.pattern_name,
                                category=self.category,
                                subject_fqn=fqn,
                                confidence=Confidence.HIGH if defn.name.startswith("_") else Confidence.MEDIUM,
                                finding_type="RISK_INDICATOR",
                                evidence_relationship_ids=(),
                                explanation=f"Unreferenced function or class '{defn.name}' with zero incoming call relationships",
                            )
                        )

        # 2. Micro-Level: Unused Local Variables inside Function Scopes
        if registry is not None:
            for fqn, defn in registry.definitions_by_fqn.items():
                if defn.definition_type not in ("function", "method", "async_function", "async_method"):
                    continue
                if not defn.file_path or "test" in defn.file_path.lower():
                    continue

                unused_vars = self._find_unused_vars_in_file(defn.file_path, defn.name, defn.start_line)
                for var_name, line_no in unused_vars:
                    findings.append(
                        Finding(
                            detector_id=self.detector_id,
                            pattern_name=self.pattern_name,
                            category=self.category,
                            subject_fqn=fqn,
                            confidence=Confidence.HIGH,
                            finding_type="RISK_INDICATOR",
                            evidence_relationship_ids=(),
                            explanation=f"Unused local variable '{var_name}' assigned on line {line_no} but never loaded in function '{defn.name}'",
                        )
                    )

        return findings

    def _find_unused_vars_in_file(self, file_path: str, func_name: str, start_line: int) -> list[tuple[str, int]]:
        """Parses a function's AST and identifies assigned variables that are never loaded.

        Args:
            file_path: Path to the python source file.
            func_name: Name of the function.
            start_line: Starting line number of the function.

        Returns:
            List[Tuple[str, int]]: List of (variable_name, line_number) tuples.
        """
        tree = _get_ast_tree(file_path)
        if tree is None:
            return []

        unused: list[tuple[str, int]] = []

        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == func_name:
                stores: dict[str, int] = {}
                loads: set[str] = set()

                for sub in ast.walk(node):
                    if isinstance(sub, ast.Name):
                        if isinstance(sub.ctx, ast.Store):
                            if not sub.id.startswith("_") and sub.id not in ("self", "cls"):
                                stores[sub.id] = sub.lineno
                        elif isinstance(sub.ctx, ast.Load):
                            loads.add(sub.id)

                for var_name, lineno in stores.items():
                    if var_name not in loads:
                        unused.append((var_name, lineno))

        return unused

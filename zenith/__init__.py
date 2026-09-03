"""ZENITH: Deterministic Static Analysis & Semantic Graph Repository Intelligence Engine."""

from pathlib import Path
from typing import Any

# Extend package search path to include src directory for full submodule resolution
_src_dir = str(Path(__file__).resolve().parent.parent / "src")
if _src_dir not in __path__:
    __path__.append(_src_dir)

__version__ = "1.0.0"


def __getattr__(name: str) -> Any:
    if name == "ScanPipeline":
        from src.pipeline.orchestrator import ScanPipeline

        return ScanPipeline
    if name == "PipelineContext":
        from src.pipeline.context import PipelineContext

        return PipelineContext
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")


__all__ = [
    "ScanPipeline",
    "PipelineContext",
]

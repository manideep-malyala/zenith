from typing import Any

import networkx as nx

from src.graph.query import GraphQueryAPI
from src.repository.scanner import MetadataFact

from .api import ApiPredicates
from .architecture import ArchitecturePredicates
from .composition import CompositionPredicates
from .concurrency import ConcurrencyPredicates
from .core import CorePredicates
from .coupling import CouplingPredicates
from .dependency import DependencyPredicates
from .exceptions import ExceptionPredicates
from .idioms import IdiomPredicates
from .inheritance import InheritancePredicates
from .metadata import MetadataPredicates
from .oop import OopPredicates
from .patterns import PatternsPredicates
from .risks import RiskPredicates


class PredicateEngine:
    """Facade for all Layer 4 derived semantic predicates."""

    def __init__(
        self,
        projections: Any,
        registry: Any,
        metadata_facts: list | None = None,
        graph_metrics: dict | None = None,
        graph: nx.MultiDiGraph | None = None,
        repo_metadata: MetadataFact | None = None,
    ):
        self.projections = projections
        self.sym_registry = registry
        self.graph = graph
        self.repo_metadata = repo_metadata
        self.graph_api = GraphQueryAPI(graph) if graph is not None else None
        self.dependency = DependencyPredicates(projections.class_dependencies, registry)
        self.inheritance = InheritancePredicates(projections.inheritance, registry)
        
        self.idioms = IdiomPredicates(projections.ast_features)
        self.concurrency = ConcurrencyPredicates(projections.ast_features, self.dependency)
        self.exceptions = ExceptionPredicates(projections.ast_features, projections.inheritance)
        
        self.core = CorePredicates(registry, projections.ast_features)
        self.composition = CompositionPredicates(projections.class_dependencies, registry)
        self.coupling = CouplingPredicates(projections.module_coupling, registry)
        self.metadata = MetadataPredicates(metadata_facts) if metadata_facts is not None else None
        self.oop = OopPredicates(self.graph_api, registry) if self.graph_api else None
        
        self.patterns = PatternsPredicates(self.core, self.idioms, self.composition, self.inheritance, self.coupling, self.oop)
        self.risks = RiskPredicates(self.core, self.idioms, self.composition, self.inheritance, self.coupling, self.graph_api, self.oop)
        self.architecture = ArchitecturePredicates(graph_metrics)
        self.api = ApiPredicates(projections.ast_features, registry)
        self.metadata = MetadataPredicates(self.repo_metadata) if self.repo_metadata else None


from typing import Any

from src.graph.models import EdgeType, ResolvedRelationship
from src.resolution.registry import GlobalSymbolRegistry

from .ast_features import ASTFeatureIndex
from .class_dependency import ClassDependencyProjection
from .inheritance import InheritanceProjection
from .models import GraphProjections
from .module_coupling import ModuleCouplingProjection
from .normalization import owner_class, owner_module


class ProjectionBuilder:
    """
    Builds the Layer 3 graph projections from Layer 2 resolved relationships.
    Enforces Invariant E1: RESOLVED/PARTIAL relationships are projected 
    wherever their endpoints can be normalized.
    """

    def build(
        self,
        relationships: list[ResolvedRelationship],
        registry: GlobalSymbolRegistry,
        all_facts: list[Any] | None = None,
    ) -> GraphProjections:
        class_deps = ClassDependencyProjection()
        inheritance = InheritanceProjection()
        module_coupling = ModuleCouplingProjection()
        ast_features = ASTFeatureIndex()
        
        if all_facts:
            ast_features.build(all_facts, registry)

        # Only process relationships that are trusted (RESOLVED or PARTIAL)
        trusted_statuses = {"RESOLVED", "PARTIAL"}
        
        for rel in relationships:
            if rel.resolution_status not in trusted_statuses:
                continue

            # Resolve endpoints to canonical classes and modules
            src_class = owner_class(rel.source_fqn, registry)
            tgt_class = owner_class(rel.target_fqn, registry)
            
            src_module = owner_module(rel.source_fqn, registry)
            tgt_module = owner_module(rel.target_fqn, registry)

            # Class Dependency Projection:
            # Requires both endpoints to normalize to local classes.
            # Allowed edge types: CALLS, INSTANTIATES, COMPOSES
            if src_class and tgt_class and rel.relationship_type in {EdgeType.CALLS, EdgeType.INSTANTIATES, EdgeType.COMPOSES}:
                class_deps.add_edge(src_class, tgt_class, rel)
                
            # Inheritance Projection:
            # Requires both endpoints to normalize to local classes.
            # Allowed edge types: INHERITS
            if src_class and tgt_class and rel.relationship_type == EdgeType.INHERITS:
                # Following the semantic direction Child --INHERITS--> Parent
                inheritance.add_edge(src_class, tgt_class, rel)
                
            # Module Coupling Projection:
            # Requires both endpoints to normalize to local modules.
            # Allowed edge types: all canonical Layer 2 edges
            if src_module and tgt_module:
                module_coupling.add_edge(src_module, tgt_module, rel)

        return GraphProjections(
            class_dependencies=class_deps,
            inheritance=inheritance,
            module_coupling=module_coupling,
            ast_features=ast_features
        )

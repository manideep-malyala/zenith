from src.core.models import CallFact, DefinitionFact, ImportFact, ResolutionStatus

from .models import EdgeType, ResolvedEdge, ResolvedRelationship, TypedEdge

# Statuses that are trusted enough to enter the typed graph
_GRAPHABLE_STATUSES = {"RESOLVED", "PARTIAL"}


class GraphBuilder:
    def __init__(self):
        import networkx as nx
        self.edges: list[TypedEdge] = []
        self.networkx_graph = nx.MultiDiGraph()

    def build_from_facts(self,
                         imports: list[ImportFact],
                         definitions: list[DefinitionFact],
                         calls: list[CallFact]):
        """
        Build legacy IMPORTS and CONTAINS edges from raw facts.
        Also produces USES_API edges (legacy, kept for graph analytics compatibility).
        New canonical CALLS/INSTANTIATES/INHERITS/COMPOSES edges come from
        build_from_relationships() after resolution.
        """
        # Build IMPORTS edges
        for imp in imports:
            edge = TypedEdge(
                source_id=imp.file_path,
                target_id=imp.module,
                edge_type=EdgeType.IMPORTS,
                evidence_fact_ids=[imp.fact_id]
            )
            self.edges.append(edge)
            self.networkx_graph.add_edge(edge.source_id, edge.target_id, key=edge.edge_id, data=edge)

        # Helper to construct fully qualified enclosing names
        def get_parent_id(file_path: str, context) -> str:
            if context and context.enclosing_class:
                return context.enclosing_class
            return file_path

        def get_enclosing_function_id(file_path: str, context) -> str:
            if context and context.enclosing_function:
                if context.enclosing_class:
                    return f"{context.enclosing_class}.{context.enclosing_function}"
                return context.enclosing_function
            return file_path

        # Build CONTAINS edges
        for df in definitions:
            parent_id = get_parent_id(df.file_path, df.context)
            if df.definition_type == "class":
                parent_id = df.file_path

            edge = TypedEdge(
                source_id=parent_id,
                target_id=df.qualified_name,
                edge_type=EdgeType.CONTAINS,
                evidence_fact_ids=[df.fact_id]
            )
            self.edges.append(edge)
            self.networkx_graph.add_edge(edge.source_id, edge.target_id, key=edge.edge_id, data=edge)

        # Build legacy USES_API edges (for backwards-compatible graph analytics)
        for call in calls:
            if call.resolution_status == ResolutionStatus.RESOLVED and call.resolved_symbol:
                source_id = get_enclosing_function_id(call.file_path, call.context)
                edge = TypedEdge(
                    source_id=source_id,
                    target_id=call.resolved_symbol,
                    edge_type=EdgeType.USES_API,
                    evidence_fact_ids=[call.fact_id]
                )
                self.edges.append(edge)
                self.networkx_graph.add_edge(edge.source_id, edge.target_id, key=edge.edge_id, data=edge)

    def build_from_relationships(self, relationships: list[ResolvedRelationship | ResolvedEdge]) -> None:
        """
        Invariant C: only RESOLVED or PARTIAL relationships enter the typed graph.
        AMBIGUOUS and UNRESOLVED relationships are preserved in knowledge.json
        (via the relationships dict) but never become TypedEdges.

        Accepts both the legacy Layer-2 ResolvedRelationship model and the
        canonical ResolvedEdge contract so the graph layer consumes one standard
        representation without callers having to scatter edge formats.
        """
        graphed = 0
        excluded = 0
        for rel in relationships:
            if isinstance(rel, ResolvedEdge):
                source_id = rel.source_id
                target_id = rel.target_id
                relationship_type = EdgeType(rel.relationship)
                status = rel.resolution_status
                evidence_fact_ids = rel.evidence_fact_ids
            else:
                source_id = rel.source_fqn
                target_id = rel.target_fqn
                relationship_type = rel.relationship_type
                status = rel.resolution_status
                evidence_fact_ids = rel.evidence_fact_ids

            if status in _GRAPHABLE_STATUSES:
                edge = TypedEdge(
                    source_id=source_id,
                    target_id=target_id,
                    edge_type=relationship_type,
                    evidence_fact_ids=evidence_fact_ids,
                )
                self.edges.append(edge)
                self.networkx_graph.add_edge(edge.source_id, edge.target_id, key=edge.edge_id, data=edge)
                graphed += 1
            else:
                excluded += 1
        return graphed, excluded

    def get_file_import_projection(self) -> list[TypedEdge]:
        """Returns only File --IMPORTS--> Module edges."""
        return [e for e in self.edges if e.edge_type == EdgeType.IMPORTS]


import networkx as nx

from src.graph.models import EdgeType, TypedEdge


class QueryResult:
    def __init__(self, nodes: set[str], edges: list[TypedEdge]):
        self.nodes = nodes
        self.edges = edges

    def get_evidence_fact_ids(self) -> set[str]:
        fact_ids = set()
        for edge in self.edges:
            fact_ids.update(edge.evidence_fact_ids)
        return fact_ids

class GraphQueryAPI:
    """
    Semantic query layer over the unified NetworkX TypedGraph.
    Provides answers to architectural, structural, and dependency questions
    while strictly preserving edge IDs and fact evidence.
    """
    def __init__(self, graph: nx.MultiDiGraph):
        self.graph = graph
        
    def _get_edges_along_path(self, path: list[str], edge_types: set[EdgeType] | None = None) -> list[TypedEdge]:
        edges = []
        for i in range(len(path) - 1):
            u = path[i]
            v = path[i+1]
            if self.graph.has_edge(u, v):
                for d in self.graph[u][v].values():
                    edge: TypedEdge = d['data']
                    if edge_types is None or edge.edge_type in edge_types:
                        edges.append(edge)
        return edges

    def _get_incoming_edges(self, node: str, edge_type: EdgeType) -> QueryResult:
        nodes = set()
        edges = []
        if node in self.graph:
            for pred in self.graph.predecessors(node):
                for d in self.graph[pred][node].values():
                    edge: TypedEdge = d['data']
                    if edge.edge_type == edge_type:
                        nodes.add(pred)
                        edges.append(edge)
        return QueryResult(nodes, edges)

    def _get_outgoing_edges(self, node: str, edge_type: EdgeType) -> QueryResult:
        nodes = set()
        edges = []
        if node in self.graph:
            for succ in self.graph.successors(node):
                for d in self.graph[node][succ].values():
                    edge: TypedEdge = d['data']
                    if edge.edge_type == edge_type:
                        nodes.add(succ)
                        edges.append(edge)
        return QueryResult(nodes, edges)

    def subclasses_of(self, class_fqn: str) -> QueryResult:
        # Child --INHERITS--> Parent. Subclasses are incoming edges.
        return self._get_incoming_edges(class_fqn, EdgeType.INHERITS)

    def methods_of(self, class_fqn: str) -> QueryResult:
        """Find methods and symbols contained within the specified class/symbol."""
        return self._get_outgoing_edges(class_fqn, EdgeType.CONTAINS)

    def contains_of(self, symbol_fqn: str) -> QueryResult:
        """Find symbols contained within the specified symbol."""
        return self._get_outgoing_edges(symbol_fqn, EdgeType.CONTAINS)

    def ancestors_of(self, class_fqn: str) -> QueryResult:
        # Transitive closure of outgoing INHERITS edges
        nodes = set()
        edges = []
        if class_fqn not in self.graph:
            return QueryResult(nodes, edges)
            
        queue = [class_fqn]
        visited = {class_fqn}
        
        while queue:
            curr = queue.pop(0)
            for succ in self.graph.successors(curr):
                for d in self.graph[curr][succ].values():
                    edge: TypedEdge = d['data']
                    if edge.edge_type == EdgeType.INHERITS:
                        edges.append(edge)
                        if succ not in visited:
                            visited.add(succ)
                            queue.append(succ)
                            nodes.add(succ)
        return QueryResult(nodes, edges)
        
    def implementations_of(self, interface_fqn: str) -> QueryResult:
        return self.subclasses_of(interface_fqn)

    def overrides_of(self, method_fqn: str) -> QueryResult:
        parts = method_fqn.split(".")
        if len(parts) < 2:
            return QueryResult(set(), [])
            
        method_name = parts[-1]
        class_fqn = ".".join(parts[:-1])
        
        # 1. Find all descendants and the path edges leading to them
        descendants = {} # desc -> list of path edges
        if class_fqn in self.graph:
            queue = [(class_fqn, [])]
            visited = {class_fqn}
            while queue:
                curr, path_edges = queue.pop(0)
                for pred in self.graph.predecessors(curr):
                    for d in self.graph[pred][curr].values():
                        edge: TypedEdge = d['data']
                        if edge.edge_type == EdgeType.INHERITS:
                            if pred not in visited:
                                visited.add(pred)
                                new_path = path_edges + [edge]
                                descendants[pred] = new_path
                                queue.append((pred, new_path))
                                
        # 2. Check which descendants actually override the method
        overriding_methods = set()
        edges = []
        for desc, path_edges in descendants.items():
            target_method = f"{desc}.{method_name}"
            if self.graph.has_edge(desc, target_method):
                for d in self.graph[desc][target_method].values():
                    edge: TypedEdge = d['data']
                    if edge.edge_type == EdgeType.CONTAINS:
                        overriding_methods.add(target_method)
                        edges.extend(path_edges)
                        edges.append(edge)
                        
        unique_edges = {e.edge_id: e for e in edges}
        return QueryResult(overriding_methods, list(unique_edges.values()))

    def callers_of(self, symbol_fqn: str) -> QueryResult:
        return self._get_incoming_edges(symbol_fqn, EdgeType.CALLS)

    def callees_of(self, symbol_fqn: str) -> QueryResult:
        return self._get_outgoing_edges(symbol_fqn, EdgeType.CALLS)
        
    def dependencies_of(self, module_fqn: str) -> QueryResult:
        return self._get_outgoing_edges(module_fqn, EdgeType.IMPORTS)

    def dependents_of(self, module_fqn: str) -> QueryResult:
        return self._get_incoming_edges(module_fqn, EdgeType.IMPORTS)

    def instantiations_of(self, type_fqn: str) -> QueryResult:
        return self._get_incoming_edges(type_fqn, EdgeType.INSTANTIATES)

    def compositions_of(self, type_fqn: str) -> QueryResult:
        return self._get_outgoing_edges(type_fqn, EdgeType.COMPOSES)

    def paths_between(self, source: str, target: str) -> list[QueryResult]:
        if source not in self.graph or target not in self.graph:
            return []
        results = []
        for path in nx.all_simple_paths(self.graph, source, target):
            edges = self._get_edges_along_path(path)
            results.append(QueryResult(set(path), edges))
        return results

    def has_cycle(self, node: str) -> QueryResult:
        if node not in self.graph:
            return QueryResult(set(), [])
        try:
            cycle_edges = nx.find_cycle(self.graph, source=node, orientation="original")
            path = []
            edges = []
            for item in cycle_edges:
                u, v, k = item[:3] # Handle 3-tuple or 4-tuple
                path.append(u)
                edges.append(self.graph[u][v][k]['data'])
            return QueryResult(set(path), edges)
        except nx.NetworkXNoCycle:
            return QueryResult(set(), [])

    # NetworkX Analytics
    def pagerank(self) -> dict[str, float]:
        return nx.pagerank(self.graph)
        
    def betweenness_centrality(self) -> dict[str, float]:
        return nx.betweenness_centrality(self.graph)
        
    def k_core(self) -> dict[str, int]:
        G = self.graph.to_undirected()
        G.remove_edges_from(nx.selfloop_edges(G))
        return nx.core_number(nx.Graph(G))
        
    def strongly_connected_components(self) -> list[list[str]]:
        return [list(c) for c in nx.strongly_connected_components(self.graph)]

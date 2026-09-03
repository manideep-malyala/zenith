from typing import Any

import networkx as nx

from src.graph.models import TypedEdge


class GraphAnalytics:
    def __init__(self, edges: list[TypedEdge]):
        """
        Expects a specific graph projection (e.g., File -> IMPORTS -> File).
        """
        self.edges = edges
        self.graph = nx.DiGraph()
        for edge in edges:
            self.graph.add_edge(edge.source_id, edge.target_id)
            
    def run_pagerank(self) -> dict[str, float]:
        if not self.graph:
            return {}
        return nx.pagerank(self.graph)
        
    def run_scc(self) -> list[list[str]]:
        if not self.graph:
            return []
        return [list(c) for c in nx.strongly_connected_components(self.graph)]
        
    def run_communities(self) -> list[list[str]]:
        if not self.graph:
            return []
        # For simplicity in v1, using weakly connected components as community approximation
        # More advanced community detection (like Louvain) requires undirected graph and specific algorithms
        return [list(c) for c in nx.weakly_connected_components(self.graph)]
        
    def run_k_core(self) -> dict[str, int]:
        if not self.graph:
            return {}
        # k-core typically runs on an undirected graph without self-loops
        G = self.graph.to_undirected()
        G.remove_edges_from(nx.selfloop_edges(G))
        return nx.core_number(G)
        
    def run_betweenness(self) -> dict[str, float]:
        if not self.graph:
            return {}
        return nx.betweenness_centrality(self.graph)

    def generate_report(self, mode: str = "standard") -> dict[str, Any]:
        """Runs metrics on the projection based on the specified mode.
        Modes:
          - fast: PageRank, SCC, K-Core
          - standard: PageRank, SCC, K-Core, Communities
          - deep: PageRank, SCC, K-Core, Communities, Betweenness
        """
        import time
        self.performance = {}
        report = {}
        
        t0 = time.time()
        pr = self.run_pagerank()
        self.performance["pagerank_seconds"] = round(time.time() - t0, 3)
        
        t0 = time.time()
        sccs = self.run_scc()
        self.performance["scc_seconds"] = round(time.time() - t0, 3)
        
        t0 = time.time()
        core = self.run_k_core()
        self.performance["k_core_seconds"] = round(time.time() - t0, 3)
        
        communities = []
        bw = {}
        
        if mode in ["standard", "deep"]:
            t0 = time.time()
            communities = self.run_communities()
            self.performance["communities_seconds"] = round(time.time() - t0, 3)
            
        if mode == "deep":
            t0 = time.time()
            bw = self.run_betweenness()
            self.performance["betweenness_seconds"] = round(time.time() - t0, 3)
        
        # Map nodes to SCC and Community IDs
        node_scc = {}
        node_scc_size = {}
        for i, scc in enumerate(sccs):
            for node in scc:
                node_scc[node] = i
                node_scc_size[node] = len(scc)
                
        node_comm = {}
        for i, comm in enumerate(communities):
            for node in comm:
                node_comm[node] = i
                
        in_degree = nx.in_degree_centrality(self.graph) if self.graph else {}
        out_degree = nx.out_degree_centrality(self.graph) if self.graph else {}

        report = {}
        for node in self.graph.nodes:
            report[node] = {
                "pagerank": pr.get(node, 0.0),
                "core_number": core.get(node, 0),
                "betweenness": bw.get(node, 0.0),
                "betweenness_centrality": bw.get(node, 0.0),
                "in_degree_centrality": in_degree.get(node, 0.0),
                "out_degree_centrality": out_degree.get(node, 0.0),
                "community_id": node_comm.get(node, -1),
                "scc_id": node_scc.get(node, -1),
                "scc_size": node_scc_size.get(node, 0)
            }
            
        return report

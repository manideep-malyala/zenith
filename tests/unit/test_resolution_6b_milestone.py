import unittest

from src.analysis.predicates.engine import PredicateEngine
from src.analysis.predicates.models import PredicateResult
from src.core.context import ASTContext
from src.core.models import (
    AssignmentFact,
    CallFact,
    DefinitionFact,
    ImportFact,
    InheritanceFact,
)
from src.graph.builder import GraphBuilder
from src.graph.models import EdgeType, ResolvedEdge, ResolvedRelationship
from src.graph.projections.builder import ProjectionBuilder
from src.resolution.registry import GlobalSymbolRegistry
from src.resolution.relationship_resolver import RelationshipResolver
from src.resolution.symbol_resolver import ScopeResolver


def _ctx(cls=None, fn=None):
    return ASTContext(enclosing_class=cls, enclosing_function=fn, loop_depth=0, conditional_depth=0)


def _resolver_for_defs(defs, imports=None, file_path="/repo/app.py"):
    registry = GlobalSymbolRegistry("/repo")
    registry.build(defs)
    import_list = imports or []
    scope_resolver = ScopeResolver(import_list, registry, file_path)
    return registry, {file_path: scope_resolver}, RelationshipResolver(registry, {file_path: scope_resolver})


class Resolution6BMilestoneTests(unittest.TestCase):
    def test_import_alias_resolves_to_external_class(self):
        defs = []
        imports = [ImportFact("/repo/a.py", 1, "concurrent.futures", "ThreadPoolExecutor", "Executor")]
        call = CallFact("/repo/a.py", 2, "Executor", None, context=_ctx())
        _, _, resolver = _resolver_for_defs(defs, imports, "/repo/a.py")

        rels = resolver.resolve_all([call], [], [])
        self.assertEqual(len(rels), 1)
        rel = rels[0]
        self.assertEqual(rel.relationship_type, EdgeType.INSTANTIATES)
        self.assertEqual(rel.target_fqn, "concurrent.futures.ThreadPoolExecutor")
        self.assertIn(rel.resolution_status, {"PARTIAL", "RESOLVED"})

    def test_internal_function_call_resolves_same_file(self):
        defs = [
            DefinitionFact("function", "a", "a", "/repo/app.py", 1, 10),
            DefinitionFact("function", "b", "b", "/repo/app.py", 11, 20),
        ]
        call = CallFact("/repo/app.py", 3, "b", None, context=_ctx(fn="a"))
        _, _, resolver = _resolver_for_defs(defs, [], "/repo/app.py")

        rels = resolver.resolve_all([call], [], [])
        self.assertEqual(len(rels), 1)
        rel = rels[0]
        self.assertEqual(rel.relationship_type, EdgeType.CALLS)
        self.assertEqual(rel.target_fqn, "app.b")

    def test_local_class_instantiation_is_instantiates(self):
        defs = [DefinitionFact("class", "User", "User", "/repo/app.py", 1, 10)]
        call = CallFact("/repo/app.py", 2, "User", None, context=_ctx())
        _, _, resolver = _resolver_for_defs(defs, [], "/repo/app.py")

        rels = resolver.resolve_all([call], [], [])
        self.assertEqual(len(rels), 1)
        rel = rels[0]
        self.assertEqual(rel.relationship_type, EdgeType.INSTANTIATES)
        self.assertEqual(rel.target_fqn, "app.User")

    def test_inheritance_resolves_base_class(self):
        defs = [
            DefinitionFact("class", "Base", "Base", "/repo/app.py", 1, 6),
            DefinitionFact("class", "Child", "Child", "/repo/app.py", 7, 12),
        ]
        inh = InheritanceFact("/repo/app.py", 7, "Child", "Base")
        _, _, resolver = _resolver_for_defs(defs, [], "/repo/app.py")

        rels = resolver.resolve_all([], [inh], [])
        self.assertEqual(len(rels), 1)
        rel = rels[0]
        self.assertEqual(rel.relationship_type, EdgeType.INHERITS)
        self.assertEqual(rel.target_fqn, "app.Base")

    def test_composition_for_self_assignment_is_emitted(self):
        defs = [DefinitionFact("class", "Repository", "Repository", "/repo/app.py", 1, 10)]
        asgn = AssignmentFact(
            "/repo/app.py",
            3,
            "assign",
            "ATTRIBUTE",
            "repo",
            has_annotation=False,
            rhs_expression="Repository()",
            context=_ctx(cls="Service"),
        )
        _, _, resolver = _resolver_for_defs(defs, [], "/repo/app.py")

        rels = resolver.resolve_all([], [], [asgn])
        self.assertEqual(len(rels), 1)
        rel = rels[0]
        self.assertEqual(rel.relationship_type, EdgeType.COMPOSES)
        self.assertEqual(rel.target_fqn, "app.Repository")

    def test_unknown_function_stays_unresolved(self):
        call = CallFact("/repo/app.py", 1, "unknown_function", None, context=_ctx())
        _, _, resolver = _resolver_for_defs([], [], "/repo/app.py")

        rels = resolver.resolve_all([call], [], [])
        self.assertEqual(len(rels), 1)
        rel = rels[0]
        self.assertEqual(rel.relationship_type, EdgeType.CALLS)
        self.assertEqual(rel.resolution_status, "UNRESOLVED")

    def test_module_attribute_call_resolves_via_imported_module_alias(self):
        defs = [
            DefinitionFact("class", "ThreadPoolExecutor", "ThreadPoolExecutor", "/repo/concurrent/futures.py", 1, 20),
        ]
        imports = [ImportFact("/repo/app.py", 1, "concurrent.futures", None, None)]
        call = CallFact("/repo/app.py", 2, "ThreadPoolExecutor", "concurrent.futures", context=_ctx())
        _, _, resolver = _resolver_for_defs(defs, imports, "/repo/app.py")

        rels = resolver.resolve_all([call], [], [])
        self.assertEqual(len(rels), 1)
        rel = rels[0]
        self.assertEqual(rel.relationship_type, EdgeType.INSTANTIATES)
        self.assertEqual(rel.target_fqn, "concurrent.futures.ThreadPoolExecutor")

    def test_resolved_edge_contract_is_accepted_by_graph_builder(self):
        graph = GraphBuilder()
        edge = ResolvedEdge(
            source_id="app.Service.create",
            target_id="app.Repository.save",
            relationship="CALLS",
            confidence=1.0,
            evidence_fact_ids=["fact-123"],
            resolution_status="RESOLVED",
        )

        graph.build_from_relationships([edge])
        self.assertEqual(len(graph.edges), 1)
        self.assertEqual(graph.edges[0].edge_type, EdgeType.CALLS)
        self.assertEqual(graph.edges[0].source_id, "app.Service.create")

    def test_ambiguous_imports_remain_ambiguous(self):
        imports = [
            ImportFact("/repo/app.py", 1, "a", "Client", None),
            ImportFact("/repo/app.py", 2, "b", "Client", None),
        ]
        call = CallFact("/repo/app.py", 3, "Client", None, context=_ctx())
        registry = GlobalSymbolRegistry("/repo")
        scope = ScopeResolver(imports, registry, "/repo/app.py")
        resolver = RelationshipResolver(registry, {"/repo/app.py": scope})

        rels = resolver.resolve_all([call], [], [])
        self.assertEqual(len(rels), 1)
        self.assertEqual(rels[0].resolution_status, "AMBIGUOUS")

    def test_predicate_result_tracks_evidence_and_confidence(self):
        result = PredicateResult(
            matched=True,
            confidence="HIGH",
            signals=("constructor_parameter", "composition"),
            evidence_fact_ids=("fact-1", "fact-2"),
            evidence_edge_ids=("edge-1", "edge-2"),
            explanation="constructor injection due to typed parameter and assignment",
        )
        self.assertTrue(result.matched)
        self.assertEqual(result.confidence, "HIGH")
        self.assertEqual(result.evidence_fact_ids, ("fact-1", "fact-2"))
        self.assertEqual(result.evidence_edge_ids, ("edge-1", "edge-2"))

    def test_predicate_engine_has_core_semantic_predicates(self):
        defs = [
            DefinitionFact("class", "Repository", "Repository", "/repo/app.py", 1, 10),
            DefinitionFact("class", "BaseRepository", "BaseRepository", "/repo/app.py", 11, 20),
            DefinitionFact("class", "Service", "Service", "/repo/app.py", 21, 40),
            DefinitionFact("class", "ChildService", "ChildService", "/repo/app.py", 41, 60),
        ]
        registry = GlobalSymbolRegistry("/repo")
        registry.build(defs)

        rels = [
            ResolvedRelationship(
                relationship_type=EdgeType.INHERITS,
                source_fqn="app.ChildService",
                target_fqn="app.BaseRepository",
                resolution_status="RESOLVED",
                resolution_domain="LOCAL",
                confidence="HIGH",
                resolution_method="EXPLICIT_IMPORT",
                evidence_fact_ids=["ei-1"],
            ),
            ResolvedRelationship(
                relationship_type=EdgeType.COMPOSES,
                source_fqn="app.Service",
                target_fqn="app.Repository",
                resolution_status="RESOLVED",
                resolution_domain="LOCAL",
                confidence="HIGH",
                resolution_method="EXPLICIT_IMPORT",
                evidence_fact_ids=["ei-2"],
            ),
            ResolvedRelationship(
                relationship_type=EdgeType.CALLS,
                source_fqn="app.Service",
                target_fqn="app.Repository",
                resolution_status="RESOLVED",
                resolution_domain="LOCAL",
                confidence="HIGH",
                resolution_method="EXPLICIT_IMPORT",
                evidence_fact_ids=["ei-3"],
            ),
        ]

        proj_builder = ProjectionBuilder()
        graphs = proj_builder.build(rels, registry)
        predicates = PredicateEngine(graphs, registry)

        self.assertTrue(predicates.inheritance.has_subclasses("app.BaseRepository").matched)
        self.assertTrue(predicates.dependency.depends_on("app.Service", "app.Repository").matched)
        self.assertTrue(predicates.dependency.delegates_to_collaborator("app.Service", "app.Repository").matched)


if __name__ == "__main__":
    unittest.main()

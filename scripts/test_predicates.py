import unittest
from src.graph.models import EdgeType, ResolvedRelationship
from src.graph.projections.builder import ProjectionBuilder
from src.resolution.registry import GlobalSymbolRegistry
from src.core.models import DefinitionFact
from src.analysis.predicates.engine import PredicateEngine
from src.analysis.predicates.models import PredicateResult

class TestPredicates(unittest.TestCase):
    def setUp(self):
        self.registry = GlobalSymbolRegistry("/fake/root")
        definitions = [
            DefinitionFact("class", "BaseRepository", "BaseRepository", "/fake/root/src/db/repo.py", 1, 1),
            DefinitionFact("class", "UserRepository", "UserRepository", "/fake/root/src/db/repo.py", 5, 5),
            DefinitionFact("class", "ProductRepository", "ProductRepository", "/fake/root/src/db/repo.py", 10, 10),
            DefinitionFact("class", "Cache", "Cache", "/fake/root/src/db/cache.py", 1, 1),
            DefinitionFact("class", "UserService", "UserService", "/fake/root/src/services/user.py", 1, 1),
            DefinitionFact("method", "save", "UserService.save", "/fake/root/src/services/user.py", 5, 5),
            DefinitionFact("method", "__init__", "UserService.__init__", "/fake/root/src/services/user.py", 2, 2),
            DefinitionFact("class", "OrderService", "OrderService", "/fake/root/src/services/order.py", 1, 1),
        ]
        self.registry.build(definitions)
        
        self.relationships = [
            ResolvedRelationship(
                relationship_type=EdgeType.INHERITS,
                source_fqn="db.repo.UserRepository",
                target_fqn="db.repo.BaseRepository",
                resolution_status="RESOLVED",
                resolution_domain="LOCAL",
                confidence="HIGH",
                resolution_method="SAME_FILE",
                evidence_fact_ids=["fact-inherits-1"]
            ),
            ResolvedRelationship(
                relationship_type=EdgeType.INHERITS,
                source_fqn="db.repo.ProductRepository",
                target_fqn="db.repo.BaseRepository",
                resolution_status="RESOLVED",
                resolution_domain="LOCAL",
                confidence="HIGH",
                resolution_method="SAME_FILE",
                evidence_fact_ids=["fact-inherits-2"]
            ),
            ResolvedRelationship(
                relationship_type=EdgeType.COMPOSES,
                source_fqn="services.user.UserService.__init__",
                target_fqn="db.cache.Cache",
                resolution_status="RESOLVED",
                resolution_domain="LOCAL",
                confidence="HIGH",
                resolution_method="EXPLICIT_IMPORT",
                evidence_fact_ids=["fact-composes-1"]
            ),
            ResolvedRelationship(
                relationship_type=EdgeType.CALLS,
                source_fqn="services.user.UserService.save",
                target_fqn="db.repo.UserRepository",
                resolution_status="RESOLVED",
                resolution_domain="LOCAL",
                confidence="HIGH",
                resolution_method="EXPLICIT_IMPORT",
                evidence_fact_ids=["fact-calls-1"]
            ),
            # Cycle between user and order services (module level)
            ResolvedRelationship(
                relationship_type=EdgeType.CALLS,
                source_fqn="services.user.UserService",
                target_fqn="services.order.OrderService",
                resolution_status="RESOLVED",
                resolution_domain="LOCAL",
                confidence="HIGH",
                resolution_method="EXPLICIT_IMPORT",
                evidence_fact_ids=["fact-calls-2"]
            ),
            ResolvedRelationship(
                relationship_type=EdgeType.CALLS,
                source_fqn="services.order.OrderService",
                target_fqn="services.user.UserService",
                resolution_status="RESOLVED",
                resolution_domain="LOCAL",
                confidence="HIGH",
                resolution_method="EXPLICIT_IMPORT",
                evidence_fact_ids=["fact-calls-3"]
            ),
        ]

        builder = ProjectionBuilder()
        self.projections = builder.build(self.relationships, self.registry)
        self.engine = PredicateEngine(self.projections, self.registry)

    def test_dependency_predicates(self):
        # Positive
        res = self.engine.dependencies.depends_on("services.user.UserService", "db.cache.Cache")
        self.assertTrue(res.matched)
        self.assertEqual(len(res.evidence_relationship_ids), 1)

        res_calls = self.engine.dependencies.calls("services.user.UserService", "db.repo.UserRepository")
        self.assertTrue(res_calls.matched)

        # Negative
        res_inst = self.engine.dependencies.instantiates("services.user.UserService", "db.cache.Cache")
        self.assertFalse(res_inst.matched)

        res_none = self.engine.dependencies.depends_on("services.user.UserService", "db.repo.BaseRepository")
        self.assertFalse(res_none.matched)

        # Bidirectional
        res_bi = self.engine.dependencies.has_bidirectional_dependency("services.user.UserService", "services.order.OrderService")
        self.assertTrue(res_bi.matched)
        self.assertEqual(len(res_bi.evidence_relationship_ids), 2)
        
        # Unique evidence relationship ids constraint
        # ensure ordering is deterministic
        self.assertEqual(res_bi.evidence_relationship_ids, tuple(sorted(res_bi.evidence_relationship_ids)))

    def test_inheritance_predicates(self):
        # Positive
        res = self.engine.inheritance.inherits_from("db.repo.UserRepository", "db.repo.BaseRepository")
        self.assertTrue(res.matched)

        # Root/Leaf
        self.assertTrue(self.engine.inheritance.is_root_class("db.repo.BaseRepository").matched)
        self.assertTrue(self.engine.inheritance.is_leaf_class("db.repo.UserRepository").matched)

        # Negative
        self.assertFalse(self.engine.inheritance.is_root_class("db.repo.UserRepository").matched)
        self.assertFalse(self.engine.inheritance.inherits_from("db.repo.BaseRepository", "db.repo.UserRepository").matched)

        # Shared parent
        res_shared = self.engine.inheritance.shares_parent("db.repo.UserRepository", "db.repo.ProductRepository")
        self.assertTrue(res_shared.matched)
        self.assertEqual(len(res_shared.evidence_relationship_ids), 2)

        # Polymorphic family
        res_poly = self.engine.inheritance.is_polymorphic_family("db.repo.BaseRepository")
        self.assertTrue(res_poly.matched)
        self.assertEqual(len(res_poly.evidence_relationship_ids), 2)

        # Negative polymorphic family
        self.assertFalse(self.engine.inheritance.is_polymorphic_family("db.repo.UserRepository").matched)

        # Hierarchy depth
        self.assertEqual(self.engine.inheritance.hierarchy_depth("db.repo.UserRepository"), 1)
        self.assertEqual(self.engine.inheritance.hierarchy_depth("db.repo.BaseRepository"), 0)

    def test_composition_predicates(self):
        # Positive
        res = self.engine.composition.is_composed_of("services.user.UserService", "db.cache.Cache")
        self.assertTrue(res.matched)
        self.assertEqual(len(res.evidence_relationship_ids), 1)

        # Negative
        self.assertFalse(self.engine.composition.is_composed_of("services.user.UserService", "db.repo.UserRepository").matched)
        self.assertFalse(self.engine.composition.is_composed_of("services.user.UserService", "int").matched)

    def test_coupling_predicates(self):
        # Fan in / out
        self.assertEqual(self.engine.coupling.fan_out("services.user"), 3) # db.cache, db.repo, services.order

        self.assertEqual(self.engine.coupling.fan_in("db.repo"), 1)

        # Cycle
        res_cyclic = self.engine.coupling.is_cyclic("services.user")
        self.assertTrue(res_cyclic.matched)
        self.assertGreaterEqual(len(res_cyclic.evidence_relationship_ids), 2)

        # Negative Cycle
        self.assertFalse(self.engine.coupling.is_cyclic("db.repo").matched)

if __name__ == '__main__':
    unittest.main()

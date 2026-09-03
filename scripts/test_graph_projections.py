import unittest
from src.graph.models import EdgeType, ResolvedRelationship
from src.graph.projections.builder import ProjectionBuilder
from src.resolution.registry import GlobalSymbolRegistry
from src.core.models import DefinitionFact

class TestGraphProjections(unittest.TestCase):
    def setUp(self):
        self.registry = GlobalSymbolRegistry("/fake/root")
        definitions = [
            DefinitionFact("class", "BaseRepository", "BaseRepository", "/fake/root/src/db/repo.py", 1, 1),
            DefinitionFact("class", "UserRepository", "UserRepository", "/fake/root/src/db/repo.py", 5, 5),
            DefinitionFact("class", "Cache", "Cache", "/fake/root/src/db/cache.py", 1, 1),
            DefinitionFact("class", "UserService", "UserService", "/fake/root/src/services/user.py", 1, 1),
            DefinitionFact("method", "save", "UserService.save", "/fake/root/src/services/user.py", 5, 5),
            DefinitionFact("method", "__init__", "UserService.__init__", "/fake/root/src/services/user.py", 2, 2),
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
        ]

    def test_class_dependency_projection(self):
        builder = ProjectionBuilder()
        projections = builder.build(self.relationships, self.registry)
        cd = projections.class_dependencies

        self.assertTrue(cd.has_dependency("services.user.UserService", "db.cache.Cache"))
        self.assertTrue(cd.has_dependency("services.user.UserService", "db.repo.UserRepository"))
        
        edges_to_repo = cd.edge_types_between("services.user.UserService", "db.repo.UserRepository")
        self.assertEqual(edges_to_repo, {EdgeType.CALLS})
        
        edges_to_cache = cd.edge_types_between("services.user.UserService", "db.cache.Cache")
        self.assertEqual(edges_to_cache, {EdgeType.COMPOSES})

        evidence = cd.evidence_between("services.user.UserService", "db.cache.Cache")
        self.assertEqual(len(evidence), 1)
        self.assertEqual(evidence[0].evidence_fact_ids, ["fact-composes-1"])

    def test_inheritance_projection(self):
        builder = ProjectionBuilder()
        projections = builder.build(self.relationships, self.registry)
        inh = projections.inheritance

        self.assertIn("db.repo.BaseRepository", inh.parents_of("db.repo.UserRepository"))
        self.assertIn("db.repo.UserRepository", inh.children_of("db.repo.BaseRepository"))
        self.assertTrue(inh.is_subclass_of("db.repo.UserRepository", "db.repo.BaseRepository"))

        evidence = inh.evidence_between("db.repo.UserRepository", "db.repo.BaseRepository")
        self.assertEqual(len(evidence), 1)
        self.assertEqual(evidence[0].relationship_type, EdgeType.INHERITS)

    def test_module_coupling_projection(self):
        builder = ProjectionBuilder()
        projections = builder.build(self.relationships, self.registry)
        mc = projections.module_coupling

        self.assertEqual(mc.coupling_between("services.user", "db.cache"), 1)
        self.assertEqual(mc.coupling_between("services.user", "db.repo"), 1)
        self.assertEqual(mc.coupling_between("db.repo", "db.repo"), 1)

        self.assertEqual(mc.fan_out("services.user"), 2)
        self.assertEqual(mc.fan_in("db.cache"), 1)

if __name__ == '__main__':
    unittest.main()

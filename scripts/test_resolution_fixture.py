"""
Smoke + fixture test for Milestone 6B resolution layer.

Validates:
1. GlobalSymbolRegistry indexes definitions and local modules correctly.
2. ScopeResolver builds import scope tables with correct domains.
3. RelationshipResolver emits correct relationship types and statuses for:
   a) INSTANTIATES (local class via explicit import)
   b) CALLS (local function via explicit import)
   c) CALLS (external: requests.get)
   d) INHERITS (local base via import)
   e) COMPOSES (self.x = LocalClass() — direct instantiation)
   f) COMPOSES (self.x: LocalClass = param — typed annotation)
   g) NO COMPOSES for self.count = 0 (primitive literal)
   h) NO COMPOSES for untyped self.param = param
   i) AMBIGUOUS when two local classes share a bare name
"""

import sys, os
sys.path.insert(0, os.path.abspath("."))

from src.core.models import (
    DefinitionFact, ImportFact, CallFact, InheritanceFact, AssignmentFact,
    ResolutionStatus, ResolutionDomain, Confidence, ResolutionMethod
)
from src.core.context import ASTContext
from src.resolution.registry import GlobalSymbolRegistry
from src.resolution.symbol_resolver import ScopeResolver
from src.resolution.relationship_resolver import RelationshipResolver
from src.graph.models import EdgeType

PASS = "\u2705"
FAIL = "\u274c"

errors = []

def check(label, condition, got=""):
    if condition:
        print(f"  {PASS} {label}")
    else:
        print(f"  {FAIL} {label}  [got: {got}]")
        errors.append(label)


# ──────────────────────────────────────────────
# Fake project root
# ──────────────────────────────────────────────
PROJECT_ROOT = "/fake/project"
USER_SVC_FILE = "/fake/project/src/services/user.py"
ORDER_SVC_FILE = "/fake/project/src/services/order.py"
REPO_FILE = "/fake/project/src/db/repo.py"
CLIENT_FILE = "/fake/project/src/api/client.py"

def make_ctx(cls=None, fn=None):
    return ASTContext(enclosing_class=cls, enclosing_function=fn, loop_depth=0, conditional_depth=0)

# ──────────────────────────────────────────────
# Definitions
# ──────────────────────────────────────────────
defs = [
    DefinitionFact("class",    "UserService",  "UserService",        USER_SVC_FILE,  1, 30),
    DefinitionFact("method",   "save",         "UserService.save",   USER_SVC_FILE, 10, 15),
    DefinitionFact("function", "create_user",  "create_user",        USER_SVC_FILE, 32, 40),
    DefinitionFact("class",    "Repository",   "Repository",         REPO_FILE,      1, 20),
    DefinitionFact("method",   "store",        "Repository.store",   REPO_FILE,     5,  8),
    # Two classes both named "Handler" — ambiguity test
    DefinitionFact("class",    "Handler",      "Handler",            USER_SVC_FILE, 42, 50),
    DefinitionFact("class",    "Handler",      "Handler",            ORDER_SVC_FILE, 1, 10),
]

registry = GlobalSymbolRegistry(PROJECT_ROOT)
registry.build(defs)

print("\n=== 1. GlobalSymbolRegistry ===")
check("services.user is local module",    registry.is_local_module("services.user"))
check("services is local module",         registry.is_local_module("services"))
check("db is local module",               registry.is_local_module("db"))
check("requests is NOT local module",     not registry.is_local_module("requests"))
check("UserService FQN resolves",         registry.lookup("services.user.UserService") is not None)
check("Repository FQN resolves",          registry.lookup("db.repo.Repository") is not None)
check("bare Handler has 2 candidates",   len(registry.lookup_name("Handler")) == 2)

# ──────────────────────────────────────────────
# Imports for CLIENT_FILE
# ──────────────────────────────────────────────
imports = [
    # from services.user import UserService
    ImportFact(CLIENT_FILE, 1, "services.user", "UserService", None),
    # from services.user import UserService as Service
    ImportFact(CLIENT_FILE, 2, "services.user", "UserService", "Service"),
    # import services.user as user_module
    ImportFact(CLIENT_FILE, 3, "services.user", None, "user_module"),
    # from db.repo import Repository
    ImportFact(CLIENT_FILE, 4, "db.repo", "Repository", None),
    # import requests  (external)
    ImportFact(CLIENT_FILE, 5, "requests", None, None),
]

scope = ScopeResolver(imports, registry, CLIENT_FILE)

print("\n=== 2. ScopeResolver ===")
e = scope.resolve("UserService")
check("UserService → LOCAL",              e and e.domain == ResolutionDomain.LOCAL, e.domain if e else "None")
check("UserService fqn correct",          e and e.fqn == "services.user.UserService", e.fqn if e else "None")
check("UserService method = EXPLICIT",    e and e.method == ResolutionMethod.EXPLICIT_IMPORT)

e2 = scope.resolve("Service")
check("Service (alias) → LOCAL",         e2 and e2.domain == ResolutionDomain.LOCAL)
check("Service fqn same as UserService", e2 and e2.fqn == "services.user.UserService")
check("Service method = ALIAS_IMPORT",   e2 and e2.method == ResolutionMethod.ALIAS_IMPORT)

e3 = scope.resolve("user_module")
check("user_module → LOCAL",             e3 and e3.domain == ResolutionDomain.LOCAL)

e4 = scope.resolve("requests")
check("requests → EXTERNAL",            e4 and e4.domain == ResolutionDomain.EXTERNAL, e4.domain if e4 else "None")

# ──────────────────────────────────────────────
# Relationships
# ──────────────────────────────────────────────
scope_resolvers = {CLIENT_FILE: scope}
resolver = RelationshipResolver(registry, scope_resolvers)

ctx_in_method = make_ctx(cls="APIClient", fn="handle")

# --- INSTANTIATES ---
call_inst = CallFact(CLIENT_FILE, 10, "UserService", None, context=ctx_in_method)
rels = resolver.resolve_all([call_inst], [], [])
r = rels[0]
print("\n=== 3a. CALLS → INSTANTIATES ===")
check("EdgeType = INSTANTIATES",          r.relationship_type == EdgeType.INSTANTIATES, r.relationship_type)
check("domain = LOCAL",                   r.resolution_domain == ResolutionDomain.LOCAL.value, r.resolution_domain)
check("confidence = HIGH",                r.confidence == Confidence.HIGH.value, r.confidence)
check("method = EXPLICIT_IMPORT",         r.resolution_method == ResolutionMethod.EXPLICIT_IMPORT.value)
check("status = RESOLVED",                r.resolution_status == ResolutionStatus.RESOLVED.value)

# --- CALLS (local function via alias) ---
call_fn = CallFact(CLIENT_FILE, 11, "create_user", None, context=ctx_in_method)
# create_user is in services.user but NOT directly imported in CLIENT_FILE — global bare-name fallback
rels2 = resolver.resolve_all([call_fn], [], [])
r2 = rels2[0]
print("\n=== 3b. CALLS (local function, bare-name fallback) ===")
check("EdgeType = CALLS",                 r2.relationship_type == EdgeType.CALLS, r2.relationship_type)
check("domain = LOCAL",                   r2.resolution_domain == ResolutionDomain.LOCAL.value)
check("confidence = MEDIUM",              r2.confidence == Confidence.MEDIUM.value, r2.confidence)

# --- CALLS (external) ---
call_ext = CallFact(CLIENT_FILE, 12, "get", "requests", context=ctx_in_method)
rels3 = resolver.resolve_all([call_ext], [], [])
r3 = rels3[0]
print("\n=== 3c. CALLS (external: requests.get) ===")
check("EdgeType = CALLS",                 r3.relationship_type == EdgeType.CALLS)
check("domain = EXTERNAL",                r3.resolution_domain == ResolutionDomain.EXTERNAL.value, r3.resolution_domain)
check("status = PARTIAL",                 r3.resolution_status == ResolutionStatus.PARTIAL.value, r3.resolution_status)

# --- INHERITS ---
inh = InheritanceFact(CLIENT_FILE, 20, "APIClient", "Repository")
rels4 = resolver.resolve_all([], [inh], [])
r4 = rels4[0]
print("\n=== 3d. INHERITS ===")
check("EdgeType = INHERITS",              r4.relationship_type == EdgeType.INHERITS, r4.relationship_type)
check("domain = LOCAL",                   r4.resolution_domain == ResolutionDomain.LOCAL.value)
check("confidence = HIGH",                r4.confidence == Confidence.HIGH.value)

# --- COMPOSES: direct instantiation ---
ctx_init = make_ctx(cls="APIClient", fn="__init__")
asgn_direct = AssignmentFact(
    CLIENT_FILE, 25, "assign", "ATTRIBUTE", "repo",
    has_annotation=False,
    rhs_expression="Repository()",
    context=ctx_init
)
rels5 = resolver.resolve_all([], [], [asgn_direct])
print("\n=== 3e. COMPOSES (direct instantiation) ===")
check("COMPOSES emitted",                 len(rels5) == 1, len(rels5))
if rels5:
    r5 = rels5[0]
    check("EdgeType = COMPOSES",          r5.relationship_type == EdgeType.COMPOSES)
    check("domain = LOCAL",               r5.resolution_domain == ResolutionDomain.LOCAL.value)
    check("confidence = HIGH",            r5.confidence == Confidence.HIGH.value)

# --- COMPOSES: typed annotation ---
asgn_typed = AssignmentFact(
    CLIENT_FILE, 26, "ann_assign", "ATTRIBUTE", "repo",
    has_annotation=True,
    annotation_expression="Repository",
    context=ctx_init
)
rels6 = resolver.resolve_all([], [], [asgn_typed])
print("\n=== 3f. COMPOSES (typed annotation) ===")
check("COMPOSES emitted",                 len(rels6) == 1, len(rels6))
if rels6:
    check("EdgeType = COMPOSES",          rels6[0].relationship_type == EdgeType.COMPOSES)
    check("confidence = HIGH",            rels6[0].confidence == Confidence.HIGH.value)

# --- NO COMPOSES: primitive literal ---
asgn_prim = AssignmentFact(
    CLIENT_FILE, 27, "assign", "ATTRIBUTE", "count",
    has_annotation=False, rhs_expression="0", context=ctx_init
)
rels7 = resolver.resolve_all([], [], [asgn_prim])
print("\n=== 3g. NO COMPOSES (primitive: self.count = 0) ===")
check("No COMPOSES emitted",              len(rels7) == 0, len(rels7))

# --- NO COMPOSES: untyped parameter ---
asgn_untyped = AssignmentFact(
    CLIENT_FILE, 28, "assign", "ATTRIBUTE", "service",
    has_annotation=False, rhs_expression="service", context=ctx_init
)
rels8 = resolver.resolve_all([], [], [asgn_untyped])
print("\n=== 3h. NO COMPOSES (untyped param: self.service = service) ===")
check("No COMPOSES emitted",              len(rels8) == 0, len(rels8))

# --- AMBIGUOUS: two local Handlers ---
call_amb = CallFact(CLIENT_FILE, 30, "Handler", None, context=ctx_in_method)
rels9 = resolver.resolve_all([call_amb], [], [])
r9 = rels9[0]
print("\n=== 3i. AMBIGUOUS (two local Handlers) ===")
check("status = AMBIGUOUS",               r9.resolution_status == ResolutionStatus.AMBIGUOUS.value, r9.resolution_status)
check("domain = AMBIGUOUS",               r9.resolution_domain == ResolutionDomain.AMBIGUOUS.value)

# ──────────────────────────────────────────────
print("\n" + "="*50)
if errors:
    print(f"FAILED: {len(errors)} check(s) failed:")
    for e in errors:
        print(f"  - {e}")
    sys.exit(1)
else:
    print(f"ALL CHECKS PASSED")

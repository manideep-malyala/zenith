# Capabilities Catalog & Declarative Registry

ZENITH evaluates **323 distinct Python capabilities** organized across 13 semantic categories.

---

## 1. Catalog Summary

| Category | Count | Resolver Engine |
|---|:---:|---|
| **1. Repository Understanding** | 14 | `MetadataPredicates` / `discovery.py` |
| **2. Complete Python Language Coverage** | 56 | `CorePredicates` (AST Definitions, Expressions, Statements) |
| **3. Python Standard Library & API Usage** | 20 | `ApiPredicates` (Dynamic Symbol & Call Matcher) |
| **4. Pythonic Idioms** | 23 | `IdiomPredicates` (Comprehensions, Context Managers, Decorators) |
| **5. Object-Oriented Design** | 7 | `OopPredicates` (Encapsulation, Delegation, Polymorphism) |
| **6. SOLID & Anti-Patterns (Risk Detectors)** | 28 | `RiskPredicates` / `DetectionEngine` (SRP, DIP, Dead Code, Circular Deps) |
| **7. GoF Design Patterns** | 42 | `PatternsPredicates` / `DetectionEngine` (Factory, Strategy, DI, Composite) |
| **8. Python-Specific Architectural Patterns** | 27 | `PatternsPredicates` (Plugin, Hook, Registry, DTO) |
| **9. Architecture & System Structure** | 29 | `ArchitecturePredicates` (PageRank, Hubs, Bridges, SCC) |
| **10. Code Quality & Maintainability** | 9 | `CorePredicates` & `ExceptionPredicates` |
| **11. Configuration Architecture** | 11 | `MetadataPredicates` (TOML, YAML, INI, Env) |
| **12. Deployment & Operational Structure** | 20 | `MetadataPredicates` (Docker, K8s, Helm, CI/CD) |
| **13. Graph Intelligence** | 10 | `GraphAnalytics` & `CouplingPredicates` |
| **Total** | **323** | **100% Fully Resolved (`PLACEHOLDER = 0`)** |

---

## 2. Declarative YAML Schema

Capabilities are declared in [`src/catalog/capabilities.yaml`](file:///Users/manideepmalyala/Documents/project-z/repo-miner/src/catalog/capabilities.yaml):

```yaml
dependency_injection:
  concept: dependency_injection
  category: 8._python-specific_/_architectural_patterns
  operations:
    - DETECT
    - EXPLAIN
  answerability: HEURISTIC
  resolver: patterns.uses_dependency_injection
  description: Dependency Injection
  learning_candidate: true
  educational_value: 0.95
```

---

## 3. Operational Integrity
All 323 capabilities are verified to have deterministic resolvers mapped to the `PredicateEngine` and GoF/Risk pattern detector registry with zero unresolvable placeholders.

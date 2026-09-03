# ZENITH Architecture & System Design

ZENITH is a deterministic static analysis and semantic graph intelligence engine for Python repositories. Instead of non-deterministic heuristic guessing or flat keyword searches, ZENITH constructs an AST-derived, graph-resolved semantic knowledge fabric and calculates graph centrality metrics to surface verifiable architectural patterns and risks.

---

## 1. End-to-End Pipeline Flow

The scanning engine executes in **5 linear phases**:

```mermaid
flowchart TD
    subgraph Phase1["1. Discovery & Parallel AST Extraction"]
        A["Target Repository / Git Clone"] --> B["Path Filtering (Excludes venv, build, cache)"]
        B --> C["ThreadPoolExecutor Parallel AST Parser"]
        C --> D["Fact Extraction (Defs, Calls, Imports, Assigns, Decorators, Async, With)"]
    end

    subgraph Phase2["2. Three-Pass Symbol & Scope Resolution"]
        D --> E["Pass 1: Global FQN Symbol Indexing (GlobalSymbolRegistry)"]
        E --> F["Pass 2: Per-File Lexical Scope & Alias Resolution (ScopeResolver)"]
        F --> G["Pass 3: Typed Edge Linking (CALLS, INHERITS, COMPOSES, IMPORTS)"]
    end

    subgraph Phase3["3. Semantic Graph & Centrality Analytics"]
        G --> H["NetworkX MultiDiGraph Construction"]
        H --> I["Subgraph Projections (File Imports, Class Dependency, Module Coupling)"]
        I --> J["5 Centrality Algorithms (PageRank, Betweenness, k-Core, Fan-In, Fan-Out)"]
    end

    subgraph Phase4["4. Unified Analysis Engine"]
        J --> K["Predicate Engine (285 Semantic Heuristics)"]
        J --> L["GoF & Risk Detectors (Factory, Strategy, Composite, DI, SRP, Dead Code)"]
    end

    subgraph Phase5["5. Top Learnings & Evidence Package Serialization"]
        K & L --> M["Unified Findings Stream"]
        M --> N["TopLearningsBuilder (Diversity Cap + Multi-Metric Graph Scoring)"]
        N --> O["EvidencePackageWriter"]
        O --> P1["metadata.json"]
        O --> P2["knowledge.json"]
        O --> P3["top_learnings.json"]
    end

    style Phase1 fill:#f8f9fa,stroke:#495057,stroke-width:1px
    style Phase2 fill:#e8f4f8,stroke:#17a2b8,stroke-width:1px
    style Phase3 fill:#eafaf1,stroke:#28a745,stroke-width:1px
    style Phase4 fill:#fef9e7,stroke:#ffc107,stroke-width:1px
    style Phase5 fill:#f4ecf7,stroke:#6f42c1,stroke-width:1px
```

---

## 2. Three-Pass Symbol & Scope Resolution Sequence

To eliminate ambiguity across imported modules, aliases, and nested scopes, ZENITH performs a deterministic 3-pass resolution protocol:

```mermaid
sequenceDiagram
    autonumber
    participant Parser as AST Extractor
    participant Registry as GlobalSymbolRegistry (Pass 1)
    participant Scope as ScopeResolver (Pass 2)
    participant Resolver as RelationshipResolver (Pass 3)
    participant Graph as NetworkX MultiDiGraph

    Parser->>Registry: Register all DefinitionFacts (FQNs & Bare Names)
    Note over Registry: Indexes FQNs & local module namespaces

    Parser->>Scope: Provide per-file ImportFacts
    Note over Scope: Maps local aliases (e.g. 'import foo as f') to target FQNs

    Parser->>Resolver: Stream CallFacts, InheritanceFacts, and AssignmentFacts
    Resolver->>Scope: Lookup receiver and symbol in local scope
    Scope-->>Resolver: Return candidate target FQN
    Resolver->>Registry: Verify existence & resolve inheritance/overrides
    Registry-->>Resolver: Confirmed target definition & domain

    Resolver->>Graph: Emit ResolvedRelationship (CALLS, INHERITS, COMPOSES)
```

---

## 3. Multi-Metric Graph Analytics & Scoring Model

To rank the most important architectural patterns, ZENITH combines 5 NetworkX centrality metrics with evidence strength and educational value:

```mermaid
flowchart LR
    subgraph GraphMetrics["5 Centrality Algorithms"]
        M1["PageRank (Authority)"]
        M2["Betweenness (Bottlenecks)"]
        M3["k-Core Decomposition (Core Cohesion)"]
        M4["In-Degree (Fan-In Coupling)"]
        M5["Out-Degree (Fan-Out Dependencies)"]
    end

    subgraph ScoringWeights["Multi-Factor Scoring Formula"]
        W1["0.30 × Confidence"]
        W2["0.30 × Graph Importance (Top-k Nodes)"]
        W3["0.20 × Educational Value"]
        W4["0.15 × Evidence Strength"]
        W5["0.05 × Log10 Occurrence Signal"]
    end

    GraphMetrics --> W2
    W1 & W2 & W3 & W4 & W5 --> FinalScore["Composite Importance Score [0.0 - 1.0]"]
    FinalScore --> Filter["Category Diversity Cap (Max 5 Per Category)"]
    Filter --> Out["top_learnings.json (Top 25 Ranked Learnings)"]
```

---

## 4. Layered Subsystems in `src/`

| Subsystem | Primary Responsibilities | Key Modules |
|---|---|---|
| **`src/core/`** | AST Parsing, Fact extraction, logging, AST token models | [`parser.py`](file:///Users/manideepmalyala/Documents/project-z/repo-miner/src/core/parser.py), [`models.py`](file:///Users/manideepmalyala/Documents/project-z/repo-miner/src/core/models.py), [`extractor.py`](file:///Users/manideepmalyala/Documents/project-z/repo-miner/src/core/extractor.py) |
| **`src/repository/`** | File discovery, ignore rules, Git provenance, metadata scanner | [`discovery.py`](file:///Users/manideepmalyala/Documents/project-z/repo-miner/src/repository/discovery.py), [`path_filters.py`](file:///Users/manideepmalyala/Documents/project-z/repo-miner/src/repository/path_filters.py), [`git.py`](file:///Users/manideepmalyala/Documents/project-z/repo-miner/src/repository/git.py) |
| **`src/resolution/`** | 3-pass symbol registry, per-file scope mapping, typed edge resolution | [`registry.py`](file:///Users/manideepmalyala/Documents/project-z/repo-miner/src/resolution/registry.py), [`symbol_resolver.py`](file:///Users/manideepmalyala/Documents/project-z/repo-miner/src/resolution/symbol_resolver.py), [`relationship_resolver.py`](file:///Users/manideepmalyala/Documents/project-z/repo-miner/src/resolution/relationship_resolver.py) |
| **`src/graph/`** | MultiDiGraph constructor, 5 centrality algorithms, projections | [`builder.py`](file:///Users/manideepmalyala/Documents/project-z/repo-miner/src/graph/builder.py), [`analytics.py`](file:///Users/manideepmalyala/Documents/project-z/repo-miner/src/graph/analytics.py), [`projections/`](file:///Users/manideepmalyala/Documents/project-z/repo-miner/src/graph/projections/) |
| **`src/analysis/`** | Semantic PredicateEngine (285 heuristics) & GoF/Risk Pattern Detectors | [`predicates/`](file:///Users/manideepmalyala/Documents/project-z/repo-miner/src/analysis/predicates/), [`detectors/`](file:///Users/manideepmalyala/Documents/project-z/repo-miner/src/analysis/detectors/) |
| **`src/catalog/`** | 323 capabilities catalog and typed capability registry | [`capabilities.yaml`](file:///Users/manideepmalyala/Documents/project-z/repo-miner/src/catalog/capabilities.yaml), [`registry.py`](file:///Users/manideepmalyala/Documents/project-z/repo-miner/src/catalog/registry.py) |
| **`src/pipeline/`** | Multi-threaded scan orchestrator coordinating all phases | [`orchestrator.py`](file:///Users/manideepmalyala/Documents/project-z/repo-miner/src/pipeline/orchestrator.py) |
| **`src/output/`** | Top learnings ranking, diversity capping, and Evidence Package writer | [`top_learnings.py`](file:///Users/manideepmalyala/Documents/project-z/repo-miner/src/output/top_learnings.py), [`writer.py`](file:///Users/manideepmalyala/Documents/project-z/repo-miner/src/output/writer.py) |

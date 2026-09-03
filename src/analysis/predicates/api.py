
from src.core.models import CallFact, ImportFact
from src.graph.projections.ast_features import ASTFeatureIndex
from src.resolution.registry import GlobalSymbolRegistry

from .models import PredicateResult


class ApiPredicates:
    """Predicates for matching Generic API/Library usage dynamically."""

    def __init__(self, ast_features: ASTFeatureIndex, registry: GlobalSymbolRegistry):
        self.ast_features = ast_features
        self.registry = registry

    def _get_module_fqn(self, fqn: str) -> str:
        defn = self.registry.lookup(fqn)
        if defn:
            return self.registry._file_to_module(defn.file_path) or ""
        return ""

    def _get_all_imports(self, fqn: str) -> list[ImportFact]:
        module_fqn = self._get_module_fqn(fqn)
        facts = list(self.ast_features.get_facts(fqn, ImportFact))
        if module_fqn and module_fqn != fqn:
            facts.extend(self.ast_features.get_facts(module_fqn, ImportFact))
        return facts

    def _resolve_name(self, receiver: str | None, name: str, imports: list[ImportFact]) -> set[str]:
        """
        Given a call like `receiver.name()` or `name()`, attempt to resolve its full qualified path
        using the available imports.
        Returns a set of possible fully qualified paths (e.g. {"concurrent.futures.ThreadPoolExecutor"}).
        """
        paths = set()
        for imp in imports:
            # 1. from X import Y
            if imp.symbol == name and receiver is None and imp.module:
                paths.add(f"{imp.module}.{name}")
            
            # 2. from X import Y as Z
            if imp.alias == name and receiver is None:
                if imp.module and imp.symbol:
                    paths.add(f"{imp.module}.{imp.symbol}")

            # 3. import X as Y -> Y.name()
            if receiver and imp.alias == receiver and imp.symbol is None:
                if imp.module:
                    paths.add(f"{imp.module}.{name}")

            # 4. import A.B -> A.B.name()
            if receiver and imp.symbol is None and imp.alias is None:
                if imp.module == receiver or imp.module.startswith(receiver + "."):
                    paths.add(f"{receiver}.{name}")
                    
        # If no import explicitly matched, it might be a built-in or full-path call, e.g. requests.get()
        if not paths:
            if receiver:
                paths.add(f"{receiver}.{name}")
            else:
                paths.add(name)
        
        return paths

    def imports_package(self, fqn: str, package: str) -> PredicateResult:
        imports = self._get_all_imports(fqn)
        matched_facts = []
        for imp in imports:
            if imp.module == package or (imp.module and imp.module.startswith(package + ".")):
                matched_facts.append(imp)
            elif imp.symbol == package: # import x.y where y is the package? Unlikely, but possible
                pass
                
        matched = bool(matched_facts)
        return PredicateResult(
            matched=matched,
            confidence="HIGH" if matched else "LOW",
            signals=(f"imports {package}",) if matched else (),
            evidence_fact_ids={f.fact_id for f in matched_facts}
        )

    def imports_symbol(self, fqn: str, package: str, symbol: str) -> PredicateResult:
        imports = self._get_all_imports(fqn)
        matched_facts = []
        for imp in imports:
            if imp.module == package and imp.symbol == symbol or imp.module == f"{package}.{symbol}" and imp.symbol is None:
                matched_facts.append(imp)
                
        matched = bool(matched_facts)
        return PredicateResult(
            matched=matched,
            confidence="HIGH" if matched else "LOW",
            signals=(f"imports {package}.{symbol}",) if matched else (),
            evidence_fact_ids={f.fact_id for f in matched_facts}
        )

    def calls_api(self, fqn: str, package: str, symbol: str) -> PredicateResult:
        imports = self._get_all_imports(fqn)
        calls = self.ast_features.get_facts(fqn, CallFact)
        
        target_path = f"{package}.{symbol}"
        matched_facts = []
        
        for call in calls:
            resolved_paths = self._resolve_name(call.receiver, call.func_name, imports)
            if target_path in resolved_paths:
                matched_facts.append(call)
                
        matched = bool(matched_facts)
        return PredicateResult(
            matched=matched,
            confidence="HIGH" if matched else "LOW",
            signals=(f"calls {target_path}",) if matched else (),
            evidence_fact_ids={f.fact_id for f in matched_facts}
        )

    def instantiates_type(self, fqn: str, package: str, type_name: str) -> PredicateResult:
        # In Python, instantiation is just calling the class constructor.
        # So it's semantically equivalent to calls_api for our static analysis,
        # but we provide this for domain clarity.
        res = self.calls_api(fqn, package, type_name)
        if res.matched:
            return PredicateResult(
                matched=True,
                confidence=res.confidence,
                signals=(f"instantiates {package}.{type_name}",),
                evidence_fact_ids=res.evidence_fact_ids
            )
        return PredicateResult(matched=False, confidence="LOW")

    def uses_module(self, fqn: str, package: str) -> PredicateResult:
        # Checks if there are ANY calls or references to the module, or if it's imported.
        # Let's just say imports_package is sufficient for "uses_module", as importing it is use.
        res = self.imports_package(fqn, package)
        if res.matched:
            return PredicateResult(
                matched=True,
                confidence="MEDIUM",
                signals=(f"uses module {package}",),
                evidence_fact_ids=res.evidence_fact_ids
            )
        return PredicateResult(matched=False, confidence="LOW")

from src.graph.models import EdgeType

from .models import PredicateResult


class PatternsPredicates:
    """Layer B: GoF Design Patterns detectors composed from Layer A OOP primitives."""
    
    def __init__(self, core, idioms, composition, inheritance, coupling, oop):
        self.core = core
        self.idioms = idioms
        self.composition = composition
        self.inheritance = inheritance
        self.coupling = coupling
        self.oop = oop

    def _result(self, class_fqn: str, pattern: str, confidence: str, signals: list, evidence: set[str], explanation: str) -> PredicateResult:
        return PredicateResult(
            matched=confidence in ("HIGH", "MEDIUM"),
            confidence=confidence,
            signals=tuple([pattern] + signals),
            evidence_fact_ids=evidence,
            explanation=f"{class_fqn} acts as a {pattern}. {explanation}"
        )

    def is_strategy(self, class_fqn: str) -> PredicateResult:
        # Strategy: Common abstraction + >= 2 implementations + context delegation
        # Here we look at the Context class (class_fqn) or the Strategy base.
        # Let's say class_fqn is the Context.
        delegates = self.oop.delegates_to_collaborator(class_fqn)
        if not delegates.matched:
            return PredicateResult(matched=False, confidence="LOW")

        # Check if any composed collaborator has interchangeable implementations
        evidence = set(delegates.evidence_fact_ids)
        signals = []
        confidence = "LOW"
        explanation = "Delegates to a collaborator, but no polymorphic implementations found."
        
        comp = self.oop.graph_api.compositions_of(class_fqn)
        for target in comp.nodes:
            inter = self.oop.has_interchangeable_implementations(target)
            if inter.matched:
                confidence = "HIGH"
                signals.append("interchangeable_strategies")
                evidence.update(inter.evidence_fact_ids)
                explanation = f"Composes {target} which has multiple strategy implementations."
                break
                
        return self._result(class_fqn, "Strategy Context", confidence, signals, evidence, explanation)

    def is_factory(self, class_fqn: str) -> PredicateResult:
        # Factory: Creates and returns objects, often abstracting the instantiation.
        creates = self.oop.creates_objects(class_fqn)
        if not creates.matched:
            return PredicateResult(matched=False, confidence="LOW")
            
        return self._result(class_fqn, "Factory", "HIGH" if "Factory" in class_fqn else "MEDIUM", 
                            ["creates_objects"], creates.evidence_fact_ids, "Instantiates objects.")

    def is_observer(self, class_fqn: str) -> PredicateResult:
        # Observer: maintains collection, registers callback, notifies subscribers
        reg = self.oop.registers_callback(class_fqn)
        noti = self.oop.notifies_subscribers(class_fqn)
        
        if not reg.matched and not noti.matched:
            return PredicateResult(matched=False, confidence="LOW")
            
        evidence = set(reg.evidence_fact_ids) | set(noti.evidence_fact_ids)
        if reg.matched and noti.matched:
            conf = "HIGH"
            exp = "Has registration and notification methods."
        else:
            conf = "MEDIUM"
            exp = "Has partial Observer behavior (either registration or notification)."
            
        return self._result(class_fqn, "Observer Subject", conf, ["pubsub"], evidence, exp)

    def is_adapter(self, class_fqn: str) -> PredicateResult:
        # Adapter: inherits target interface, composes adaptee, delegates to it.
        delegates = self.oop.delegates_to_collaborator(class_fqn)
        has_base = self.oop.has_abstract_base(class_fqn)
        
        if not delegates.matched:
            return PredicateResult(matched=False, confidence="LOW")
            
        evidence = set(delegates.evidence_fact_ids) | set(has_base.evidence_fact_ids)
        if has_base.matched:
            return self._result(class_fqn, "Adapter", "HIGH", ["translates_interface"], evidence, "Inherits base and delegates to composed object.")
        return self._result(class_fqn, "Adapter", "MEDIUM", ["delegation"], evidence, "Delegates to composed object, but no explicit target interface found.")

    def is_decorator(self, class_fqn: str) -> PredicateResult:
        # GoF Decorator: composes an interface and inherits the SAME interface
        parents = self.oop.graph_api.ancestors_of(class_fqn)
        composed = self.oop.graph_api.compositions_of(class_fqn)
        
        shared = parents.nodes.intersection(composed.nodes)
        if not shared:
            return PredicateResult(matched=False, confidence="LOW")
            
        evidence = parents.get_evidence_fact_ids() | composed.get_evidence_fact_ids()
        return self._result(class_fqn, "Decorator", "HIGH", ["wraps_same_interface"], evidence, f"Composes and inherits {shared}.")

    def is_facade(self, class_fqn: str) -> PredicateResult:
        # Facade: Wraps multiple subsystems. 
        comp = self.oop.graph_api.compositions_of(class_fqn)
        if len(comp.nodes) >= 3:
            return self._result(class_fqn, "Facade", "MEDIUM", ["aggregates_subsystem"], comp.get_evidence_fact_ids(), "Composes multiple distinct objects.")
        return PredicateResult(matched=False, confidence="LOW")

    def is_command(self, class_fqn: str) -> PredicateResult:
        # Encapsulates a request.
        overrides = self.oop.has_method_overrides(class_fqn)
        name_match = "Command" in class_fqn
        methods = self.oop.graph_api._get_outgoing_edges(class_fqn, EdgeType.CONTAINS)
        has_execute = any(m.split(".")[-1] in ("execute", "run", "do") for m in methods.nodes)
        
        if name_match and has_execute:
            evidence = set(overrides.evidence_fact_ids) | set(methods.get_evidence_fact_ids())
            return self._result(class_fqn, "Command", "HIGH", ["encapsulates_request"], evidence, "Has Command name and execute method.")
        if has_execute and overrides.matched:
            return self._result(class_fqn, "Command", "MEDIUM", [], set(overrides.evidence_fact_ids) | set(methods.get_evidence_fact_ids()), "Overrides a method and has an execute-like method.")
            
        return PredicateResult(matched=False, confidence="LOW")

    def is_builder(self, class_fqn: str) -> PredicateResult:
        methods = self.oop.graph_api._get_outgoing_edges(class_fqn, EdgeType.CONTAINS)
        build_methods = [m for m in methods.nodes if m.split(".")[-1].startswith("add_") or m.split(".")[-1].startswith("with_")]
        has_build = any(m.split(".")[-1] == "build" for m in methods.nodes)
        
        if build_methods and has_build:
            return self._result(class_fqn, "Builder", "HIGH", ["fluent_interface"], methods.get_evidence_fact_ids(), "Has build and accumulator methods.")
        return PredicateResult(matched=False, confidence="LOW")

    def is_proxy(self, class_fqn: str) -> PredicateResult:
        return self.is_decorator(class_fqn) # structurally identical

    def is_singleton(self, class_fqn: str) -> PredicateResult:
        methods = self.oop.graph_api._get_outgoing_edges(class_fqn, EdgeType.CONTAINS)
        has_instance = any(m.split(".")[-1] in ("get_instance", "instance") for m in methods.nodes)
        if has_instance:
            return self._result(class_fqn, "Singleton", "MEDIUM", ["controlled_instantiation"], methods.get_evidence_fact_ids(), "Has get_instance method.")
        return PredicateResult(matched=False, confidence="LOW")

    def is_template_method(self, class_fqn: str) -> PredicateResult:
        # Base class that calls its own abstract methods (which are overridden by subclasses)
        # We can just look if it has subclasses and delegates to self methods.
        subs = self.oop.graph_api.subclasses_of(class_fqn)
        if subs.nodes:
            return self._result(class_fqn, "Template Method Base", "MEDIUM", ["inversion_of_control"], subs.get_evidence_fact_ids(), "Has subclasses.")
        return PredicateResult(matched=False, confidence="LOW")

    def is_state(self, class_fqn: str) -> PredicateResult:
        return self.is_strategy(class_fqn) # structurally similar

    def is_composite(self, class_fqn: str) -> PredicateResult:
        # Composes a collection of its own base type
        return self.is_decorator(class_fqn)

    def is_abstract_factory(self, class_fqn: str) -> PredicateResult:
        methods = self.oop.graph_api._get_outgoing_edges(class_fqn, EdgeType.CONTAINS)
        factory_methods = [m for m in methods.nodes if m.split(".")[-1].startswith("create_")]
        if len(factory_methods) >= 2:
            return self._result(class_fqn, "Abstract Factory", "MEDIUM", ["multiple_factory_methods"], methods.get_evidence_fact_ids(), "Has multiple create methods.")
        return PredicateResult(matched=False, confidence="LOW")

    def is_chain_of_responsibility(self, class_fqn: str) -> PredicateResult:
        return self.is_decorator(class_fqn) # structurally wraps same interface and delegates

    def is_mediator(self, class_fqn: str) -> PredicateResult:
        comp = self.oop.graph_api.compositions_of(class_fqn)
        if len(comp.nodes) >= 2:
            return self._result(class_fqn, "Mediator", "MEDIUM", ["centralized_communication"], comp.get_evidence_fact_ids(), "Composes multiple colleagues.")
        return PredicateResult(matched=False, confidence="LOW")

    def is_visitor(self, class_fqn: str) -> PredicateResult:
        methods = self.oop.graph_api._get_outgoing_edges(class_fqn, EdgeType.CONTAINS)
        visit_methods = [m for m in methods.nodes if m.split(".")[-1].startswith("visit_")]
        if visit_methods:
            return self._result(class_fqn, "Visitor", "HIGH", ["double_dispatch"], methods.get_evidence_fact_ids(), "Has visit_ methods.")
        return PredicateResult(matched=False, confidence="LOW")

    def is_bridge(self, class_fqn: str) -> PredicateResult:
        # Abstraction composes Implementor
        return self.is_adapter(class_fqn)

    def is_flyweight(self, class_fqn: str) -> PredicateResult:
        if "Flyweight" in class_fqn:
            return self._result(class_fqn, "Flyweight", "HIGH", ["shared_state"], set(), "Name indicates Flyweight.")
        return PredicateResult(matched=False, confidence="LOW")

    def is_iterator(self, class_fqn: str) -> PredicateResult:
        methods = self.oop.graph_api._get_outgoing_edges(class_fqn, EdgeType.CONTAINS)
        has_iter = any(m.split(".")[-1] in ("__iter__", "next", "__next__") for m in methods.nodes)
        if has_iter:
            return self._result(class_fqn, "Iterator", "HIGH", ["iteration_protocol"], methods.get_evidence_fact_ids(), "Implements iterator protocol.")
        return PredicateResult(matched=False, confidence="LOW")

    def is_prototype(self, class_fqn: str) -> PredicateResult:
        methods = self.oop.graph_api._get_outgoing_edges(class_fqn, EdgeType.CONTAINS)
        has_clone = any(m.split(".")[-1] in ("clone", "__deepcopy__", "__copy__") for m in methods.nodes)
        if has_clone:
            return self._result(class_fqn, "Prototype", "HIGH", ["cloning"], methods.get_evidence_fact_ids(), "Implements clone method.")
        return PredicateResult(matched=False, confidence="LOW")

    def is_interpreter(self, class_fqn: str) -> PredicateResult:
        if not self.oop or not self.oop.graph_api:
            return PredicateResult(matched=False, confidence="LOW")
        methods = self.oop.graph_api._get_outgoing_edges(class_fqn, EdgeType.CONTAINS)
        has_interpret = any(m.split(".")[-1] in ("interpret", "eval", "evaluate") for m in methods.nodes)
        if has_interpret:
            return self._result(class_fqn, "Interpreter", "HIGH", ["grammar_interpretation"], methods.get_evidence_fact_ids(), "Implements interpret/evaluate method.")
        return PredicateResult(matched=False, confidence="LOW")

    def is_memento(self, class_fqn: str) -> PredicateResult:
        if not self.oop or not self.oop.graph_api:
            return PredicateResult(matched=False, confidence="LOW")
        methods = self.oop.graph_api._get_outgoing_edges(class_fqn, EdgeType.CONTAINS)
        has_state = any(m.split(".")[-1] in ("get_state", "set_state", "save_state", "restore_state") for m in methods.nodes)
        if has_state or "Memento" in class_fqn:
            return self._result(class_fqn, "Memento", "HIGH", ["state_snapshot"], methods.get_evidence_fact_ids(), "Captures and restores object internal state.")
        return PredicateResult(matched=False, confidence="LOW")

    def uses_dependency_injection(self, class_fqn: str) -> PredicateResult:
        if not self.oop or not self.oop.graph_api:
            return PredicateResult(matched=False, confidence="LOW")
        comp = self.oop.graph_api.compositions_of(class_fqn)
        if comp and comp.nodes:
            return self._result(class_fqn, "Dependency Injection", "HIGH", ["constructor_injection"], comp.get_evidence_fact_ids(), "Injects collaborators via composition.")
        return PredicateResult(matched=False, confidence="LOW")

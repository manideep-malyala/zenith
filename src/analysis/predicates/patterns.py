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

    def _has_oop(self) -> bool:
        return self.oop is not None and getattr(self.oop, "graph_api", None) is not None

    def _result(
        self,
        class_fqn: str,
        pattern: str,
        confidence: str,
        signals: list,
        evidence: set[str],
        explanation: str,
    ) -> PredicateResult:
        return PredicateResult(
            matched=confidence in ("HIGH", "MEDIUM"),
            confidence=confidence,
            signals=tuple([pattern] + signals),
            evidence_fact_ids=evidence,
            explanation=f"{class_fqn} acts as a {pattern}. {explanation}",
        )

    def is_strategy(self, class_fqn: str) -> PredicateResult:
        if not self._has_oop():
            return PredicateResult(matched=False, confidence="LOW", explanation="OOP projection graph unavailable.")

        delegates = self.oop.delegates_to_collaborator(class_fqn)
        if not delegates.matched:
            return PredicateResult(matched=False, confidence="LOW")

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
        if not self._has_oop():
            return PredicateResult(matched=False, confidence="LOW", explanation="OOP projection graph unavailable.")

        creates = self.oop.creates_objects(class_fqn)
        if not creates.matched:
            return PredicateResult(matched=False, confidence="LOW")

        methods = self.oop.graph_api.methods_of(class_fqn)
        has_factory_method = any(
            m.split(".")[-1].startswith("create_")
            or m.split(".")[-1].startswith("build_")
            or m.split(".")[-1].startswith("get_")
            for m in methods.nodes
        )
        has_name_signal = "Factory" in class_fqn or "Builder" in class_fqn

        confidence = "HIGH" if (has_factory_method or has_name_signal) else "MEDIUM"
        signals = ["creates_objects"]
        if has_factory_method:
            signals.append("factory_method")

        evidence = set(creates.evidence_fact_ids) | set(methods.get_evidence_fact_ids())
        return self._result(
            class_fqn,
            "Factory",
            confidence,
            signals,
            evidence,
            "Instantiates and returns objects through controlled factory methods.",
        )

    def is_observer(self, class_fqn: str) -> PredicateResult:
        if not self._has_oop():
            return PredicateResult(matched=False, confidence="LOW", explanation="OOP projection graph unavailable.")

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
        if not self._has_oop():
            return PredicateResult(matched=False, confidence="LOW", explanation="OOP projection graph unavailable.")

        delegates = self.oop.delegates_to_collaborator(class_fqn)
        has_base = self.oop.has_abstract_base(class_fqn)

        if not delegates.matched:
            return PredicateResult(matched=False, confidence="LOW")

        evidence = set(delegates.evidence_fact_ids) | set(has_base.evidence_fact_ids)
        if has_base.matched:
            return self._result(
                class_fqn,
                "Adapter",
                "HIGH",
                ["translates_interface"],
                evidence,
                "Inherits base and delegates to composed object.",
            )
        return self._result(
            class_fqn,
            "Adapter",
            "MEDIUM",
            ["delegation"],
            evidence,
            "Delegates to composed object, but no explicit target interface found.",
        )

    def is_decorator(self, class_fqn: str) -> PredicateResult:
        if not self._has_oop():
            return PredicateResult(matched=False, confidence="LOW", explanation="OOP projection graph unavailable.")

        parents = self.oop.graph_api.ancestors_of(class_fqn)
        composed = self.oop.graph_api.compositions_of(class_fqn)

        shared = parents.nodes.intersection(composed.nodes)
        if not shared:
            return PredicateResult(matched=False, confidence="LOW")

        evidence = parents.get_evidence_fact_ids() | composed.get_evidence_fact_ids()
        return self._result(
            class_fqn,
            "Decorator",
            "HIGH",
            ["wraps_same_interface"],
            evidence,
            f"Composes and inherits {shared}.",
        )

    def is_facade(self, class_fqn: str) -> PredicateResult:
        if not self._has_oop():
            return PredicateResult(matched=False, confidence="LOW", explanation="OOP projection graph unavailable.")

        comp = self.oop.graph_api.compositions_of(class_fqn)
        if len(comp.nodes) >= 3:
            return self._result(
                class_fqn,
                "Facade",
                "MEDIUM",
                ["aggregates_subsystem"],
                comp.get_evidence_fact_ids(),
                "Composes multiple distinct subsystem objects.",
            )
        return PredicateResult(matched=False, confidence="LOW")

    def is_command(self, class_fqn: str) -> PredicateResult:
        if not self._has_oop():
            return PredicateResult(matched=False, confidence="LOW", explanation="OOP projection graph unavailable.")

        overrides = self.oop.has_method_overrides(class_fqn)
        name_match = "Command" in class_fqn or "Action" in class_fqn or "Task" in class_fqn
        methods = self.oop.graph_api.methods_of(class_fqn)
        has_execute = any(m.split(".")[-1] in ("execute", "run", "do", "__call__") for m in methods.nodes)

        if name_match and has_execute:
            evidence = set(overrides.evidence_fact_ids) | set(methods.get_evidence_fact_ids())
            return self._result(
                class_fqn,
                "Command",
                "HIGH",
                ["encapsulates_request"],
                evidence,
                "Has Command naming and execution dispatch method.",
            )
        if has_execute and overrides.matched:
            return self._result(
                class_fqn,
                "Command",
                "MEDIUM",
                ["encapsulates_request"],
                set(overrides.evidence_fact_ids) | set(methods.get_evidence_fact_ids()),
                "Overrides a method and provides execution dispatch.",
            )

        return PredicateResult(matched=False, confidence="LOW")

    def is_builder(self, class_fqn: str) -> PredicateResult:
        if not self._has_oop():
            return PredicateResult(matched=False, confidence="LOW", explanation="OOP projection graph unavailable.")

        methods = self.oop.graph_api.methods_of(class_fqn)
        build_methods = [
            m
            for m in methods.nodes
            if m.split(".")[-1].startswith("add_")
            or m.split(".")[-1].startswith("with_")
            or m.split(".")[-1].startswith("set_")
        ]
        has_build = any(m.split(".")[-1] in ("build", "create", "construct") for m in methods.nodes)

        if build_methods and has_build:
            return self._result(
                class_fqn,
                "Builder",
                "HIGH",
                ["fluent_interface"],
                methods.get_evidence_fact_ids(),
                "Has build method and method chaining accumulators.",
            )
        return PredicateResult(matched=False, confidence="LOW")

    def is_proxy(self, class_fqn: str) -> PredicateResult:
        if not self._has_oop():
            return PredicateResult(matched=False, confidence="LOW", explanation="OOP projection graph unavailable.")

        decorator_res = self.is_decorator(class_fqn)
        if not decorator_res.matched:
            return PredicateResult(matched=False, confidence="LOW")

        # Proxy controls access to the target
        return self._result(
            class_fqn,
            "Proxy",
            "MEDIUM",
            ["controls_access", "surrogate"],
            decorator_res.evidence_fact_ids,
            "Provides surrogate interface for target collaborator.",
        )

    def is_singleton(self, class_fqn: str) -> PredicateResult:
        if not self._has_oop():
            return PredicateResult(matched=False, confidence="LOW", explanation="OOP projection graph unavailable.")

        methods = self.oop.graph_api.methods_of(class_fqn)
        has_instance = any(m.split(".")[-1] in ("get_instance", "instance", "__new__") for m in methods.nodes)
        has_name = "Singleton" in class_fqn

        if has_instance or has_name:
            conf = "HIGH" if (has_instance and has_name) else "MEDIUM"
            return self._result(
                class_fqn,
                "Singleton",
                conf,
                ["controlled_instantiation"],
                methods.get_evidence_fact_ids(),
                "Has controlled instance accessor or singleton metadata.",
            )
        return PredicateResult(matched=False, confidence="LOW")

    def is_template_method(self, class_fqn: str) -> PredicateResult:
        if not self._has_oop():
            return PredicateResult(matched=False, confidence="LOW", explanation="OOP projection graph unavailable.")

        subs = self.oop.graph_api.subclasses_of(class_fqn)
        if subs.nodes:
            return self._result(
                class_fqn,
                "Template Method Base",
                "MEDIUM",
                ["inversion_of_control"],
                subs.get_evidence_fact_ids(),
                "Defines abstract algorithm structure overridden by subclasses.",
            )
        return PredicateResult(matched=False, confidence="LOW")

    def is_state(self, class_fqn: str) -> PredicateResult:
        if not self._has_oop():
            return PredicateResult(matched=False, confidence="LOW", explanation="OOP projection graph unavailable.")

        strat_res = self.is_strategy(class_fqn)
        if not strat_res.matched:
            return PredicateResult(matched=False, confidence="LOW")

        return self._result(
            class_fqn,
            "State Context",
            "MEDIUM",
            ["state_transitions"],
            strat_res.evidence_fact_ids,
            "Encapsulates state-dependent polymorphic behavior.",
        )

    def is_composite(self, class_fqn: str) -> PredicateResult:
        if not self._has_oop():
            return PredicateResult(matched=False, confidence="LOW", explanation="OOP projection graph unavailable.")

        dec_res = self.is_decorator(class_fqn)
        if not dec_res.matched:
            return PredicateResult(matched=False, confidence="LOW")

        return self._result(
            class_fqn,
            "Composite",
            "MEDIUM",
            ["recursive_aggregation"],
            dec_res.evidence_fact_ids,
            "Aggregates child components of identical interface.",
        )

    def is_abstract_factory(self, class_fqn: str) -> PredicateResult:
        if not self._has_oop():
            return PredicateResult(matched=False, confidence="LOW", explanation="OOP projection graph unavailable.")

        methods = self.oop.graph_api.methods_of(class_fqn)
        factory_methods = [
            m
            for m in methods.nodes
            if m.split(".")[-1].startswith("create_") or m.split(".")[-1].startswith("build_")
        ]
        if len(factory_methods) >= 2:
            return self._result(
                class_fqn,
                "Abstract Factory",
                "HIGH" if len(factory_methods) >= 3 else "MEDIUM",
                ["multiple_factory_methods"],
                methods.get_evidence_fact_ids(),
                f"Declares {len(factory_methods)} distinct object creation methods.",
            )
        return PredicateResult(matched=False, confidence="LOW")

    def is_chain_of_responsibility(self, class_fqn: str) -> PredicateResult:
        if not self._has_oop():
            return PredicateResult(matched=False, confidence="LOW", explanation="OOP projection graph unavailable.")

        dec_res = self.is_decorator(class_fqn)
        if not dec_res.matched:
            return PredicateResult(matched=False, confidence="LOW")

        return self._result(
            class_fqn,
            "Chain of Responsibility",
            "MEDIUM",
            ["sequential_delegation"],
            dec_res.evidence_fact_ids,
            "Delegates unhandled requests to successor in handler chain.",
        )

    def is_mediator(self, class_fqn: str) -> PredicateResult:
        if not self._has_oop():
            return PredicateResult(matched=False, confidence="LOW", explanation="OOP projection graph unavailable.")

        comp = self.oop.graph_api.compositions_of(class_fqn)
        if len(comp.nodes) >= 2:
            return self._result(
                class_fqn,
                "Mediator",
                "MEDIUM",
                ["centralized_communication"],
                comp.get_evidence_fact_ids(),
                "Composes and coordinates multiple colleagues.",
            )
        return PredicateResult(matched=False, confidence="LOW")

    def is_visitor(self, class_fqn: str) -> PredicateResult:
        if not self._has_oop():
            return PredicateResult(matched=False, confidence="LOW", explanation="OOP projection graph unavailable.")

        methods = self.oop.graph_api.methods_of(class_fqn)
        visit_methods = [m for m in methods.nodes if m.split(".")[-1].startswith("visit_")]
        if visit_methods:
            return self._result(
                class_fqn,
                "Visitor",
                "HIGH",
                ["double_dispatch"],
                methods.get_evidence_fact_ids(),
                f"Declares {len(visit_methods)} visitor handler methods.",
            )
        return PredicateResult(matched=False, confidence="LOW")

    def is_bridge(self, class_fqn: str) -> PredicateResult:
        if not self._has_oop():
            return PredicateResult(matched=False, confidence="LOW", explanation="OOP projection graph unavailable.")

        return self.is_adapter(class_fqn)

    def is_flyweight(self, class_fqn: str) -> PredicateResult:
        if not self._has_oop():
            return PredicateResult(matched=False, confidence="LOW", explanation="OOP projection graph unavailable.")

        methods = self.oop.graph_api.methods_of(class_fqn)
        has_cache_method = any(m.split(".")[-1] in ("get", "get_flyweight", "lookup") for m in methods.nodes)
        has_name = "Flyweight" in class_fqn

        if has_cache_method or has_name:
            return self._result(
                class_fqn,
                "Flyweight",
                "HIGH" if (has_cache_method and has_name) else "MEDIUM",
                ["shared_state"],
                methods.get_evidence_fact_ids(),
                "Provides shared flyweight instances to minimize memory usage.",
            )
        return PredicateResult(matched=False, confidence="LOW")

    def is_iterator(self, class_fqn: str) -> PredicateResult:
        if not self._has_oop():
            return PredicateResult(matched=False, confidence="LOW", explanation="OOP projection graph unavailable.")

        methods = self.oop.graph_api.methods_of(class_fqn)
        has_iter = any(m.split(".")[-1] in ("__iter__", "next", "__next__") for m in methods.nodes)
        if has_iter:
            return self._result(
                class_fqn,
                "Iterator",
                "HIGH",
                ["iteration_protocol"],
                methods.get_evidence_fact_ids(),
                "Implements standard Python iteration protocol (__iter__ / __next__).",
            )
        return PredicateResult(matched=False, confidence="LOW")

    def is_prototype(self, class_fqn: str) -> PredicateResult:
        if not self._has_oop():
            return PredicateResult(matched=False, confidence="LOW", explanation="OOP projection graph unavailable.")

        methods = self.oop.graph_api.methods_of(class_fqn)
        has_clone = any(m.split(".")[-1] in ("clone", "__deepcopy__", "__copy__", "copy") for m in methods.nodes)
        if has_clone:
            return self._result(
                class_fqn,
                "Prototype",
                "HIGH",
                ["cloning"],
                methods.get_evidence_fact_ids(),
                "Implements cloning protocol for prototype duplication.",
            )
        return PredicateResult(matched=False, confidence="LOW")

    def is_interpreter(self, class_fqn: str) -> PredicateResult:
        if not self._has_oop():
            return PredicateResult(matched=False, confidence="LOW", explanation="OOP projection graph unavailable.")

        methods = self.oop.graph_api.methods_of(class_fqn)
        has_interpret = any(m.split(".")[-1] in ("interpret", "eval", "evaluate", "parse") for m in methods.nodes)
        if has_interpret:
            return self._result(
                class_fqn,
                "Interpreter",
                "HIGH",
                ["grammar_interpretation"],
                methods.get_evidence_fact_ids(),
                "Implements grammar evaluation and interpretation protocol.",
            )
        return PredicateResult(matched=False, confidence="LOW")

    def is_memento(self, class_fqn: str) -> PredicateResult:
        if not self._has_oop():
            return PredicateResult(matched=False, confidence="LOW", explanation="OOP projection graph unavailable.")

        methods = self.oop.graph_api.methods_of(class_fqn)
        has_state = any(
            m.split(".")[-1] in ("get_state", "set_state", "save_state", "restore_state", "snapshot")
            for m in methods.nodes
        )
        if has_state or "Memento" in class_fqn or "Snapshot" in class_fqn:
            return self._result(
                class_fqn,
                "Memento",
                "HIGH",
                ["state_snapshot"],
                methods.get_evidence_fact_ids(),
                "Captures and restores internal object state snapshots.",
            )
        return PredicateResult(matched=False, confidence="LOW")

    def uses_dependency_injection(self, class_fqn: str) -> PredicateResult:
        if not self._has_oop():
            return PredicateResult(matched=False, confidence="LOW", explanation="OOP projection graph unavailable.")

        comp = self.oop.graph_api.compositions_of(class_fqn)
        if comp and comp.nodes:
            return self._result(
                class_fqn,
                "Dependency Injection",
                "HIGH",
                ["constructor_injection"],
                comp.get_evidence_fact_ids(),
                "Injects external collaborators via composition.",
            )
        return PredicateResult(matched=False, confidence="LOW")

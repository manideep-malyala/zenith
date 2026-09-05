from src.graph.query import GraphQueryAPI
from src.resolution.registry import GlobalSymbolRegistry

from .models import PredicateResult


class OopPredicates:
    """Layer A: Reusable OOP/Design predicates built on the GraphQueryAPI."""

    def __init__(self, graph_api: GraphQueryAPI | None, registry: GlobalSymbolRegistry):
        self.graph_api = graph_api
        self.registry = registry

    def _has_graph(self) -> bool:
        return self.graph_api is not None and getattr(self.graph_api, "graph", None) is not None

    def _result(
        self,
        matched: bool,
        signals: list[str],
        evidence_fact_ids: set[str] | None = None,
        explanation: str = "",
    ) -> PredicateResult:
        return PredicateResult(
            matched=matched,
            confidence="HIGH" if matched else "LOW",
            signals=tuple(signals) if matched else (),
            evidence_fact_ids=evidence_fact_ids or set(),
            explanation=explanation,
        )

    def has_multiple_inheritance(self, class_fqn: str) -> PredicateResult:
        if not self._has_graph():
            return self._result(False, [])
        res = self.graph_api.direct_bases_of(class_fqn)
        matched = len(res.nodes) > 1
        return self._result(
            matched,
            ["multiple_inheritance"],
            res.get_evidence_fact_ids(),
            f"{class_fqn} inherits from multiple base classes: {res.nodes}" if matched else "",
        )

    def has_abstract_base(self, class_fqn: str) -> PredicateResult:
        if not self._has_graph():
            return self._result(False, [])
        res = self.graph_api.ancestors_of(class_fqn)
        for node in res.nodes:
            if "ABC" in node or "Protocol" in node:
                return self._result(
                    True,
                    ["has_abstract_base"],
                    res.get_evidence_fact_ids(),
                    f"Inherits from abstract base {node}",
                )
        return self._result(False, [])

    def implements_protocol(self, class_fqn: str) -> PredicateResult:
        if not self._has_graph():
            return self._result(False, [])
        res = self.graph_api.ancestors_of(class_fqn)
        for node in res.nodes:
            if "Protocol" in node:
                return self._result(
                    True,
                    ["implements_protocol"],
                    res.get_evidence_fact_ids(),
                    f"Implements protocol {node}",
                )
        return self._result(False, [])

    def has_method_overrides(self, class_fqn: str) -> PredicateResult:
        if not self._has_graph():
            return self._result(False, [])
        res = self.graph_api.ancestors_of(class_fqn)
        ancestor_methods = set()
        ancestor_contains_edges = []
        for ancestor in res.nodes:
            methods = self.graph_api.methods_of(ancestor)
            for m in methods.nodes:
                ancestor_methods.add(m.split(".")[-1])
            ancestor_contains_edges.extend(methods.edges)

        my_methods_res = self.graph_api.methods_of(class_fqn)
        overrides = []
        for m in my_methods_res.nodes:
            if m.split(".")[-1] in ancestor_methods:
                overrides.append(m)

        matched = bool(overrides)
        evidence = res.get_evidence_fact_ids() | my_methods_res.get_evidence_fact_ids()
        for edge in ancestor_contains_edges:
            evidence.update(edge.evidence_fact_ids)

        return self._result(
            matched,
            ["method_overrides"],
            evidence,
            f"Overrides methods: {overrides}" if matched else "",
        )

    def creates_objects(self, class_fqn: str) -> PredicateResult:
        if not self._has_graph():
            return self._result(False, [])
        res = self.graph_api.instances_created_by(class_fqn)
        methods = self.graph_api.methods_of(class_fqn)
        for m in methods.nodes:
            m_res = self.graph_api.instances_created_by(m)
            res.nodes.update(m_res.nodes)
            res.edges.extend(m_res.edges)

        matched = len(res.nodes) > 0
        return self._result(
            matched,
            ["creates_objects"],
            res.get_evidence_fact_ids(),
            f"Instantiates {res.nodes}" if matched else "",
        )

    def has_factory_method(self, class_fqn: str) -> PredicateResult:
        return self.creates_objects(class_fqn)

    def returns_constructed_object(self, class_fqn: str) -> PredicateResult:
        return self.creates_objects(class_fqn)

    def wraps_collaborator(self, class_fqn: str) -> PredicateResult:
        if not self._has_graph():
            return self._result(False, [])
        res = self.graph_api.compositions_of(class_fqn)
        matched = len(res.nodes) > 0
        return self._result(
            matched,
            ["wraps_collaborator"],
            res.get_evidence_fact_ids(),
            f"Composes {res.nodes}" if matched else "",
        )

    def delegates_to_collaborator(self, class_fqn: str) -> PredicateResult:
        if not self._has_graph():
            return self._result(False, [])
        comp_res = self.graph_api.compositions_of(class_fqn)
        if not comp_res.nodes:
            return self._result(False, [])

        methods = self.graph_api.methods_of(class_fqn)
        called = set()
        call_edges = []
        for m in methods.nodes:
            calls = self.graph_api.callees_of(m)
            for target in calls.nodes:
                target_base = ".".join(target.split(".")[:-1])
                if target_base in comp_res.nodes:
                    called.add(target)
                    call_edges.extend(calls.edges)

        matched = bool(called)
        evidence = comp_res.get_evidence_fact_ids() | {
            e.evidence_fact_ids[0] for e in call_edges if e.evidence_fact_ids
        }
        return self._result(
            matched,
            ["delegates"],
            evidence,
            f"Delegates to {called}" if matched else "",
        )

    def maintains_collection(self, class_fqn: str) -> PredicateResult:
        return self.wraps_collaborator(class_fqn)

    def registers_callback(self, class_fqn: str) -> PredicateResult:
        if not self._has_graph():
            return self._result(False, [])
        methods = self.graph_api.methods_of(class_fqn)
        for m in methods.nodes:
            name = m.split(".")[-1].lower()
            if "register" in name or "attach" in name or "subscribe" in name or "add_listener" in name:
                return self._result(
                    True,
                    ["registers_callback"],
                    methods.get_evidence_fact_ids(),
                    f"Has registration method {m}",
                )
        return self._result(False, [])

    def notifies_subscribers(self, class_fqn: str) -> PredicateResult:
        if not self._has_graph():
            return self._result(False, [])
        methods = self.graph_api.methods_of(class_fqn)
        for m in methods.nodes:
            name = m.split(".")[-1].lower()
            if "notify" in name or "update" in name or "emit" in name or "dispatch" in name or "broadcast" in name:
                return self._result(
                    True,
                    ["notifies_subscribers"],
                    methods.get_evidence_fact_ids(),
                    f"Has notification method {m}",
                )
        return self._result(False, [])

    def has_shared_interface(self, fqn_a: str, fqn_b: str) -> PredicateResult:
        if not self._has_graph():
            return self._result(False, [])
        anc_a = self.graph_api.ancestors_of(fqn_a)
        anc_b = self.graph_api.ancestors_of(fqn_b)
        shared = anc_a.nodes.intersection(anc_b.nodes)
        if "object" in shared:
            shared.remove("object")

        matched = bool(shared)
        evidence = anc_a.get_evidence_fact_ids() | anc_b.get_evidence_fact_ids()
        return self._result(
            matched,
            ["shared_interface"],
            evidence,
            f"Shared ancestors: {shared}" if matched else "",
        )

    def has_interchangeable_implementations(self, base_fqn: str) -> PredicateResult:
        if not self._has_graph():
            return self._result(False, [])
        res = self.graph_api.subclasses_of(base_fqn)
        matched = len(res.nodes) >= 2
        return self._result(
            matched,
            ["interchangeable"],
            res.get_evidence_fact_ids(),
            f"Has {len(res.nodes)} implementations" if matched else "",
        )

    def translates_interface(self, adapter_fqn: str, adaptee_fqn: str) -> PredicateResult:
        if not self._has_graph():
            return self._result(False, [])
        comp = self.graph_api.compositions_of(adapter_fqn)
        if adaptee_fqn in comp.nodes:
            return self._result(
                True,
                ["translates"],
                comp.get_evidence_fact_ids(),
                f"{adapter_fqn} composes {adaptee_fqn}",
            )
        return self._result(False, [])

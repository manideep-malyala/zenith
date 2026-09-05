import networkx as nx

from src.graph.query import GraphQueryAPI

from .models import PredicateResult


class RiskPredicates:
    """Phase 5: SOLID Risk and Anti-Pattern Intelligence."""

    def __init__(self, core, idioms, composition, inheritance, coupling, graph_api: GraphQueryAPI | None, oop):
        self.core = core
        self.idioms = idioms
        self.composition = composition
        self.inheritance = inheritance
        self.coupling = coupling
        self.graph_api = graph_api
        self.oop = oop

    def _has_graph(self) -> bool:
        return self.graph_api is not None and getattr(self.graph_api, "graph", None) is not None

    def _has_oop(self) -> bool:
        return self.oop is not None

    def _risk_result(
        self,
        class_fqn: str,
        risk_name: str,
        confidence: str,
        matched: bool,
        signals: list,
        evidence: set[str],
        explanation: str,
    ) -> PredicateResult:
        return PredicateResult(
            matched=matched,
            confidence=confidence,
            signals=tuple(["RISK_INDICATOR", risk_name] + signals) if matched else (),
            evidence_fact_ids=evidence,
            explanation=f"[{risk_name}] {explanation}" if matched else "",
        )

    # --- Reusable Risk Metrics ---

    def method_count(self, class_fqn: str) -> tuple[int, set[str]]:
        if not self._has_graph():
            return 0, set()
        res = self.graph_api.methods_of(class_fqn)
        return len(res.nodes), res.get_evidence_fact_ids()

    def fan_out(self, class_fqn: str) -> tuple[int, set[str]]:
        if not self._has_graph():
            return 0, set()
        comp = self.graph_api.compositions_of(class_fqn)
        inst = self.graph_api.instances_created_by(class_fqn)
        # Combine unique targets
        nodes = comp.nodes | inst.nodes
        evidence = comp.get_evidence_fact_ids() | inst.get_evidence_fact_ids()

        # Also check method calls
        methods = self.graph_api.methods_of(class_fqn)
        for m in methods.nodes:
            calls = self.graph_api.callees_of(m)
            for c in calls.nodes:
                target_base = ".".join(c.split(".")[:-1])
                if target_base and target_base != class_fqn:
                    nodes.add(target_base)
            evidence.update(calls.get_evidence_fact_ids())

        return len(nodes), evidence

    def fan_in(self, class_fqn: str) -> tuple[int, set[str]]:
        if not self._has_graph():
            return 0, set()
        comp_in = self.graph_api.compositions_incoming(class_fqn)
        inst_in = self.graph_api.instantiations_of(class_fqn)
        nodes = comp_in.nodes | inst_in.nodes
        evidence = comp_in.get_evidence_fact_ids() | inst_in.get_evidence_fact_ids()
        return len(nodes), evidence

    def dependency_diversity(self, class_fqn: str) -> tuple[int, set[str]]:
        count, evidence = self.fan_out(class_fqn)
        return count, evidence

    def branch_complexity(self, class_fqn: str) -> tuple[int, set[str]]:
        cond = self.core.uses_conditional(class_fqn)
        loop = self.core.uses_loop(class_fqn)
        score = 0
        if cond.matched:
            score += 1
        if loop.matched:
            score += 1
        return score, set(cond.evidence_fact_ids) | set(loop.evidence_fact_ids)

    def class_size(self, class_fqn: str) -> tuple[int, set[str]]:
        mc, ev_mc = self.method_count(class_fqn)
        return mc, ev_mc

    def inheritance_depth(self, class_fqn: str) -> tuple[int, set[str]]:
        if not self._has_graph() or class_fqn not in self.graph_api.graph:
            return 0, set()
        try:
            length = nx.shortest_path_length(self.graph_api.graph, source="object", target=class_fqn)
            return length, set()
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            anc = self.graph_api.ancestors_of(class_fqn)
            return len(anc.nodes), anc.get_evidence_fact_ids()

    def responsibility_diversity(self, class_fqn: str) -> tuple[int, set[str]]:
        score = 0
        evidence = set()
        io_read = self.core.uses_file_reads(class_fqn)
        io_write = self.core.uses_file_writes(class_fqn)
        net = self.core.uses_sockets(class_fqn)
        db = self.core.uses_sqlite3(class_fqn)
        if io_read.matched or io_write.matched:
            score += 1
            evidence.update(io_read.evidence_fact_ids)
            evidence.update(io_write.evidence_fact_ids)
        if net.matched:
            score += 1
            evidence.update(net.evidence_fact_ids)
        if db.matched:
            score += 1
            evidence.update(db.evidence_fact_ids)

        return score, evidence

    # --- SOLID Risks ---

    def has_srp_risk(self, class_fqn: str) -> PredicateResult:
        resp, ev_resp = self.responsibility_diversity(class_fqn)
        mc, ev_mc = self.method_count(class_fqn)
        fout, ev_fout = self.fan_out(class_fqn)

        matched = (resp > 1 and mc > 5) or (fout > 7 and mc > 10)
        return self._risk_result(
            class_fqn,
            "SRP Risk",
            "MEDIUM" if matched else "LOW",
            matched,
            ["srp_risk"],
            ev_resp | ev_mc | ev_fout,
            f"Responsibility diversity: {resp}, Method count: {mc}, Fan-out: {fout}",
        )

    def has_ocp_risk(self, class_fqn: str) -> PredicateResult:
        type_checks = self.idioms.uses_type_checking(class_fqn)
        bc, ev_bc = self.branch_complexity(class_fqn)

        matched = type_checks.matched and bc > 0
        return self._risk_result(
            class_fqn,
            "OCP Risk",
            "MEDIUM" if matched else "LOW",
            matched,
            ["ocp_risk"],
            set(type_checks.evidence_fact_ids) | ev_bc,
            f"Uses type-checking (isinstance) combined with branch complexity {bc}.",
        )

    def has_lsp_risk(self, class_fqn: str) -> PredicateResult:
        if not self._has_oop():
            return self._risk_result(class_fqn, "LSP Risk", "LOW", False, ["lsp_risk"], set(), "")
        overrides = self.oop.has_method_overrides(class_fqn)
        raises = self.core.uses_raise(class_fqn)

        matched = overrides.matched and raises.matched
        return self._risk_result(
            class_fqn,
            "LSP Risk",
            "LOW",
            matched,
            ["lsp_risk"],
            set(overrides.evidence_fact_ids) | set(raises.evidence_fact_ids),
            "Overrides methods and raises exceptions (potential contract violation).",
        )

    def has_isp_risk(self, class_fqn: str) -> PredicateResult:
        if not self._has_graph():
            return self._risk_result(class_fqn, "ISP Risk", "LOW", False, ["isp_risk"], set(), "")
        mc, ev_mc = self.method_count(class_fqn)
        subs = self.graph_api.subclasses_of(class_fqn)

        matched = mc > 10 and len(subs.nodes) > 2
        return self._risk_result(
            class_fqn,
            "ISP Risk",
            "MEDIUM" if matched else "LOW",
            matched,
            ["isp_risk"],
            ev_mc | subs.get_evidence_fact_ids(),
            f"Fat interface: {mc} methods with {len(subs.nodes)} subclasses.",
        )

    def has_dip_risk(self, class_fqn: str) -> PredicateResult:
        if not self._has_graph():
            return self._risk_result(class_fqn, "DIP Risk", "LOW", False, ["dip_risk"], set(), "")
        fout, ev_fout = self.fan_out(class_fqn)
        comp = self.graph_api.compositions_of(class_fqn)
        concrete_deps = 0
        for c in comp.nodes:
            if not self.graph_api.subclasses_of(c).nodes:
                concrete_deps += 1

        matched = concrete_deps > 3 and fout > 4
        return self._risk_result(
            class_fqn,
            "DIP Risk",
            "MEDIUM" if matched else "LOW",
            matched,
            ["dip_risk"],
            ev_fout | comp.get_evidence_fact_ids(),
            f"High coupling to concrete implementations: {concrete_deps} out of {fout} total fan-out.",
        )

    # --- Anti-Patterns ---

    def has_god_class(self, class_fqn: str) -> PredicateResult:
        mc, ev_mc = self.method_count(class_fqn)
        fout, ev_fout = self.fan_out(class_fqn)
        resp, ev_resp = self.responsibility_diversity(class_fqn)

        matched = mc > 15 and fout > 7 and resp >= 1
        return self._risk_result(
            class_fqn,
            "God Class",
            "HIGH" if matched else "LOW",
            matched,
            ["god_class"],
            ev_mc | ev_fout | ev_resp,
            f"Method count: {mc}, Fan-out: {fout}, Responsibility diversity: {resp}.",
        )

    def has_god_method(self, class_fqn: str) -> PredicateResult:
        bc, ev_bc = self.branch_complexity(class_fqn)
        matched = bc >= 2
        return self._risk_result(
            class_fqn,
            "God Method / Complexity",
            "LOW",
            matched,
            ["complex_method"],
            ev_bc,
            f"Class exhibits high branch complexity ({bc}).",
        )

    def has_feature_envy(self, class_fqn: str) -> PredicateResult:
        if not self._has_graph() or not self._has_oop():
            return self._risk_result(class_fqn, "Feature Envy", "LOW", False, ["feature_envy"], set(), "")
        comp = self.graph_api.compositions_of(class_fqn)
        delegates = self.oop.delegates_to_collaborator(class_fqn)
        matched = len(comp.nodes) == 1 and delegates.matched
        return self._risk_result(
            class_fqn,
            "Feature Envy",
            "LOW",
            matched,
            ["feature_envy"],
            comp.get_evidence_fact_ids() | set(delegates.evidence_fact_ids),
            f"Strong delegation to single composed dependency {comp.nodes}.",
        )

    def has_long_method(self, class_fqn: str) -> PredicateResult:
        return self.has_god_method(class_fqn)

    def has_shotgun_surgery(self, class_fqn: str) -> PredicateResult:
        fin, ev_fin = self.fan_in(class_fqn)
        matched = fin > 10
        return self._risk_result(
            class_fqn,
            "Shotgun Surgery",
            "MEDIUM" if matched else "LOW",
            matched,
            ["shotgun_surgery"],
            ev_fin,
            f"High fan-in ({fin}); changing this class may affect many others.",
        )

    def has_divergent_change(self, class_fqn: str) -> PredicateResult:
        return self.has_srp_risk(class_fqn)

    def has_primitive_obsession(self, class_fqn: str) -> PredicateResult:
        json_use = self.core.uses_json(class_fqn)
        return self._risk_result(
            class_fqn,
            "Primitive Obsession",
            "LOW",
            json_use.matched,
            ["primitive_obsession"],
            set(json_use.evidence_fact_ids),
            "Heavy use of generic dicts/JSON instead of typed objects.",
        )

    def has_speculative_generality(self, class_fqn: str) -> PredicateResult:
        if not self._has_graph() or not self._has_oop():
            return self._risk_result(class_fqn, "Speculative Generality", "LOW", False, ["speculative_generality"], set(), "")
        anc = self.oop.has_abstract_base(class_fqn)
        subs = self.graph_api.subclasses_of(class_fqn)
        matched = anc.matched and len(subs.nodes) == 0
        return self._risk_result(
            class_fqn,
            "Speculative Generality",
            "MEDIUM" if matched else "LOW",
            matched,
            ["speculative_generality"],
            set(anc.evidence_fact_ids) | subs.get_evidence_fact_ids(),
            "Abstract interface with 0 implementations.",
        )

    def has_circular_dependency(self, class_fqn: str) -> PredicateResult:
        if not self._has_graph():
            return self._risk_result(class_fqn, "Circular Dependency", "LOW", False, ["circular_dependency"], set(), "")
        cycle = self.graph_api.has_cycle(class_fqn)
        matched = len(cycle.nodes) > 0
        return self._risk_result(
            class_fqn,
            "Circular Dependency",
            "HIGH" if matched else "LOW",
            matched,
            ["circular_dependency"],
            cycle.get_evidence_fact_ids(),
            f"Participates in cycle: {cycle.nodes}",
        )

    def has_excessive_coupling(self, class_fqn: str) -> PredicateResult:
        fout, ev_fout = self.fan_out(class_fqn)
        matched = fout > 10
        return self._risk_result(
            class_fqn,
            "Excessive Coupling",
            "HIGH" if matched else "LOW",
            matched,
            ["excessive_coupling"],
            ev_fout,
            f"Fan-out is {fout}.",
        )

    # Maintain existing generic stubs mapped from capabilities.yaml
    def has_rigid_extension_points(self, class_fqn: str) -> PredicateResult:
        return self.has_speculative_generality(class_fqn)

    def has_fat_interface(self, class_fqn: str) -> PredicateResult:
        return self.has_isp_risk(class_fqn)

    def has_concrete_dependency_coupling(self, class_fqn: str) -> PredicateResult:
        return self.has_dip_risk(class_fqn)

    def has_fragile_base_class(self, class_fqn: str) -> PredicateResult:
        return self.has_god_class(class_fqn)

    def has_excessive_responsibility(self, class_fqn: str) -> PredicateResult:
        return self.has_srp_risk(class_fqn)

    def has_excessive_abstraction(self, class_fqn: str) -> PredicateResult:
        depth, ev = self.inheritance_depth(class_fqn)
        matched = depth > 4
        return self._risk_result(
            class_fqn,
            "Excessive Abstraction",
            "MEDIUM" if matched else "LOW",
            matched,
            ["deep_inheritance"],
            ev,
            f"Inheritance depth is {depth}.",
        )

    def has_speculative_abstraction(self, class_fqn: str) -> PredicateResult:
        return self.has_speculative_generality(class_fqn)

    def has_type_switch_heavy_design(self, class_fqn: str) -> PredicateResult:
        return self.has_ocp_risk(class_fqn)

    def has_subclass_contract_violation(self, class_fqn: str) -> PredicateResult:
        return self.has_lsp_risk(class_fqn)

    def has_possibly_unreferenced_symbol(self, class_fqn: str) -> PredicateResult:
        fin, ev = self.fan_in(class_fqn)
        matched = fin == 0
        return self._risk_result(
            class_fqn,
            "Unreferenced Symbol",
            "LOW",
            matched,
            ["unreferenced"],
            ev,
            "Symbol has 0 internal callers.",
        )

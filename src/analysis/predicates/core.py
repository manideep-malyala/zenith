from src.core.models import (
    AssignmentFact,
    CallFact,
    ConditionalFact,
    LoopFact,
    ReturnFact,
    TryFact,
)
from src.graph.projections.ast_features import ASTFeatureIndex
from src.resolution.registry import GlobalSymbolRegistry

from .models import PredicateResult


class CorePredicates:
    """Predicates covering fundamental Python language features."""
    def __init__(self, registry: GlobalSymbolRegistry, ast_features: ASTFeatureIndex):
        self.registry = registry
        self.ast_features = ast_features

    def _basic_def_check(self, fqn: str, def_type: str, signal: str) -> PredicateResult:
        defn = self.registry.lookup(fqn)
        matched = defn is not None and defn.definition_type == def_type
        return PredicateResult(
            matched=matched,
            confidence="HIGH" if matched else "LOW",
            signals=(signal,) if matched else (),
            explanation=f"{fqn} is a {signal}." if matched else f"{fqn} is not a {signal}."
        )

    def is_function(self, fqn: str) -> PredicateResult:
        return self._basic_def_check(fqn, "function", "function")

    def is_method(self, fqn: str) -> PredicateResult:
        return self._basic_def_check(fqn, "method", "method")

    def is_class(self, fqn: str) -> PredicateResult:
        return self._basic_def_check(fqn, "class", "class")

    def is_async_function(self, fqn: str) -> PredicateResult:
        defn = self.registry.lookup(fqn)
        matched = defn is not None and defn.definition_type in ("function", "method") and getattr(defn, "is_async", False)
        return PredicateResult(
            matched=matched,
            confidence="HIGH" if matched else "LOW",
            signals=("async_function",) if matched else (),
            explanation=f"{fqn} is an async function." if matched else f"{fqn} is not an async function."
        )

    def uses_assignment(self, fqn: str) -> PredicateResult:
        facts = self.ast_features.get_facts(fqn, AssignmentFact)
        matched = bool(facts)
        return PredicateResult(
            matched=matched,
            confidence="HIGH" if matched else "LOW",
            signals=("assignment",) if matched else (),
            evidence_fact_ids={f.fact_id for f in facts},
            explanation=f"{fqn} contains assignments." if matched else f"{fqn} does not contain assignments."
        )

    def uses_conditional(self, fqn: str) -> PredicateResult:
        facts = self.ast_features.get_facts(fqn, ConditionalFact)
        matched = bool(facts)
        return PredicateResult(
            matched=matched,
            confidence="HIGH" if matched else "LOW",
            signals=("conditional",) if matched else (),
            evidence_fact_ids={f.fact_id for f in facts},
            explanation=f"{fqn} contains conditional statements (if/match)." if matched else f"{fqn} does not contain conditionals."
        )

    def uses_loop(self, fqn: str) -> PredicateResult:
        facts = self.ast_features.get_facts(fqn, LoopFact)
        matched = bool(facts)
        return PredicateResult(
            matched=matched,
            confidence="HIGH" if matched else "LOW",
            signals=("loop",) if matched else (),
            evidence_fact_ids={f.fact_id for f in facts},
            explanation=f"{fqn} contains loops (for/while)." if matched else f"{fqn} does not contain loops."
        )

    def uses_return(self, fqn: str) -> PredicateResult:
        facts = self.ast_features.get_facts(fqn, ReturnFact)
        matched = bool(facts)
        return PredicateResult(
            matched=matched,
            confidence="HIGH" if matched else "LOW",
            signals=("return",) if matched else (),
            evidence_fact_ids={f.fact_id for f in facts},
            explanation=f"{fqn} uses return statements." if matched else f"{fqn} does not use return statements."
        )

    def uses_break(self, fqn: str) -> PredicateResult:
        facts = self.ast_features.get_facts(fqn, LoopFact)
        break_facts = [f for f in facts if f.has_break]
        matched = bool(break_facts)
        return PredicateResult(
            matched=matched,
            confidence="HIGH" if matched else "LOW",
            signals=("break",) if matched else (),
            evidence_fact_ids={f.fact_id for f in break_facts},
            explanation=f"{fqn} uses break statements." if matched else f"{fqn} does not use break statements."
        )

    def uses_continue(self, fqn: str) -> PredicateResult:
        facts = self.ast_features.get_facts(fqn, LoopFact)
        continue_facts = [f for f in facts if f.has_continue]
        matched = bool(continue_facts)
        return PredicateResult(
            matched=matched,
            confidence="HIGH" if matched else "LOW",
            signals=("continue",) if matched else (),
            evidence_fact_ids={f.fact_id for f in continue_facts},
            explanation=f"{fqn} uses continue statements." if matched else f"{fqn} does not use continue statements."
        )

    def uses_match_case(self, fqn: str) -> PredicateResult:
        facts = self.ast_features.get_facts(fqn, ConditionalFact)
        match_facts = [f for f in facts if f.kind == 'match']
        matched = bool(match_facts)
        return PredicateResult(
            matched=matched,
            confidence="HIGH" if matched else "LOW",
            signals=("match_case",) if matched else (),
            evidence_fact_ids={f.fact_id for f in match_facts},
            explanation=f"{fqn} uses pattern matching (match/case)." if matched else f"{fqn} does not use match/case."
        )

    def uses_annotated_assignment(self, fqn: str) -> PredicateResult:
        facts = self.ast_features.get_facts(fqn, AssignmentFact)
        ann_facts = [f for f in facts if f.kind == 'ann_assign']
        matched = bool(ann_facts)
        return PredicateResult(
            matched=matched,
            confidence="HIGH" if matched else "LOW",
            signals=("annotated_assignment",) if matched else (),
            evidence_fact_ids={f.fact_id for f in ann_facts},
            explanation=f"{fqn} uses annotated assignments." if matched else f"{fqn} does not use annotated assignments."
        )

    def uses_augmented_assignment(self, fqn: str) -> PredicateResult:
        facts = self.ast_features.get_facts(fqn, AssignmentFact)
        aug_facts = [f for f in facts if f.kind == 'aug_assign']
        matched = bool(aug_facts)
        return PredicateResult(
            matched=matched,
            confidence="HIGH" if matched else "LOW",
            signals=("augmented_assignment",) if matched else (),
            evidence_fact_ids={f.fact_id for f in aug_facts},
            explanation=f"{fqn} uses augmented assignments." if matched else f"{fqn} does not use augmented assignments."
        )

    def uses_walrus_expression(self, fqn: str) -> PredicateResult:
        facts = self.ast_features.get_facts(fqn, AssignmentFact)
        walrus_facts = [f for f in facts if f.kind == 'named_expr']
        matched = bool(walrus_facts)
        return PredicateResult(
            matched=matched,
            confidence="HIGH" if matched else "LOW",
            signals=("walrus_expression",) if matched else (),
            evidence_fact_ids={f.fact_id for f in walrus_facts},
            explanation=f"{fqn} uses walrus expressions (:=)." if matched else f"{fqn} does not use walrus expressions."
        )

    def uses_function_calls(self, fqn: str) -> PredicateResult:
        facts = self.ast_features.get_facts(fqn, CallFact)
        # Function calls typically don't have a receiver, or their resolved symbol points to a function
        # A naive heuristic for function calls: receiver is None
        func_calls = [f for f in facts if f.receiver is None]
        matched = bool(func_calls)
        return PredicateResult(
            matched=matched,
            confidence="MEDIUM" if matched else "LOW",
            signals=("function_call",) if matched else (),
            evidence_fact_ids={f.fact_id for f in func_calls},
            explanation=f"{fqn} makes function calls." if matched else f"{fqn} does not make function calls."
        )

    def uses_method_calls(self, fqn: str) -> PredicateResult:
        facts = self.ast_features.get_facts(fqn, CallFact)
        # Method calls typically have a receiver (e.g. obj.method())
        method_calls = [f for f in facts if f.receiver is not None]
        matched = bool(method_calls)
        return PredicateResult(
            matched=matched,
            confidence="MEDIUM" if matched else "LOW",
            signals=("method_call",) if matched else (),
            evidence_fact_ids={f.fact_id for f in method_calls},
            explanation=f"{fqn} makes method calls." if matched else f"{fqn} does not make method calls."
        )

    def has_object_lifecycle(self, fqn: str) -> PredicateResult:
        # Check if the class defines magic lifecycle methods
        lifecycle_methods = {"__init__", "__new__", "__del__", "__enter__", "__exit__"}
        prefix = fqn + "."
        found = []
        for reg_fqn, defn in self.registry.definitions_by_fqn.items():
            if defn.definition_type == "method" and reg_fqn.startswith(prefix) and reg_fqn.count(".") == prefix.count("."):
                if defn.name in lifecycle_methods:
                    found.append(defn.name)
                    
        matched = bool(found)
        return PredicateResult(
            matched=matched,
            confidence="HIGH" if matched else "LOW",
            signals=("object_lifecycle",) if matched else (),
            explanation=f"{fqn} implements lifecycle methods: {found}." if matched else f"{fqn} does not implement lifecycle methods."
        )

    def is_factory_method(self, fqn: str) -> PredicateResult:
        # Heuristic: a method that is a @classmethod, or a function named *factory* or create*
        # Actually, let's just check if it's a classmethod for now.
        defn = self.registry.lookup(fqn)
        if not defn or defn.definition_type != "method":
            return PredicateResult(matched=False, confidence="LOW", explanation=f"{fqn} is not a method.")
            
        # We need to check if it has a @classmethod decorator
        from src.core.models import DecoratorFact
        facts = self.ast_features.get_facts(fqn, DecoratorFact)
        is_classmethod = any(f.target_name == defn.name and f.decorator_expression == "classmethod" for f in facts)
        
        return PredicateResult(
            matched=is_classmethod,
            confidence="MEDIUM" if is_classmethod else "LOW",
            signals=("factory_method",) if is_classmethod else (),
            evidence_fact_ids={f.fact_id for f in facts if f.decorator_expression == "classmethod"},
            explanation=f"{fqn} is a @classmethod, often used as a factory method." if is_classmethod else f"{fqn} is not a @classmethod."
        )

    # --- newly added predicates ---

    def has_except_star(self, fqn: str) -> PredicateResult:
        facts = self.ast_features.get_facts(fqn, TryFact)
        star_facts = [f for f in facts if f.is_star]
        matched = bool(star_facts)
        return PredicateResult(matched=matched, confidence="HIGH" if matched else "LOW", signals=("except*",) if matched else (), evidence_fact_ids={f.fact_id for f in star_facts})

    def has_exception_hierarchy(self, fqn: str) -> PredicateResult:
        from src.core.models import InheritanceFact
        facts = self.ast_features.get_facts(fqn, InheritanceFact)
        exc = [f for f in facts if "Exception" in f.base_expression or "Error" in f.base_expression]
        matched = bool(exc)
        return PredicateResult(matched=matched, confidence="MEDIUM" if matched else "LOW", signals=("exception_hierarchy",) if matched else (), evidence_fact_ids={f.fact_id for f in exc})

    def has_exception_propagation(self, fqn: str) -> PredicateResult:
        from src.core.models import RaiseFact
        facts = self.ast_features.get_facts(fqn, RaiseFact)
        # Propagation: either raise without exception (re-raise) or raising a new exception with 'from'
        prop = [f for f in facts if f.exception_expression is None or f.cause is not None]
        matched = bool(prop)
        return PredicateResult(matched=matched, confidence="HIGH" if matched else "LOW", signals=("exception_propagation",) if matched else (), evidence_fact_ids={f.fact_id for f in prop})

    def has_with(self, fqn: str) -> PredicateResult:
        from src.core.models import WithFact
        facts = self.ast_features.get_facts(fqn, WithFact)
        matched = bool(facts)
        return PredicateResult(matched=matched, confidence="HIGH" if matched else "LOW", signals=("with",) if matched else (), evidence_fact_ids={f.fact_id for f in facts})

    def has_async_with(self, fqn: str) -> PredicateResult:
        from src.core.models import WithFact
        facts = self.ast_features.get_facts(fqn, WithFact)
        awith = [f for f in facts if f.is_async]
        matched = bool(awith)
        return PredicateResult(matched=matched, confidence="HIGH" if matched else "LOW", signals=("async_with",) if matched else (), evidence_fact_ids={f.fact_id for f in awith})

    def has_nested_context_managers(self, fqn: str) -> PredicateResult:
        from src.core.models import WithFact
        facts = self.ast_features.get_facts(fqn, WithFact)
        nested = [f for f in facts if f.items_count > 1] # e.g. with A() as a, B() as b:
        matched = bool(nested)
        return PredicateResult(matched=matched, confidence="HIGH" if matched else "LOW", signals=("nested_context_managers",) if matched else (), evidence_fact_ids={f.fact_id for f in nested})

    def has_resource_cleanup(self, fqn: str) -> PredicateResult:
        from src.core.models import WithFact
        with_facts = self.ast_features.get_facts(fqn, WithFact)
        try_facts = self.ast_features.get_facts(fqn, TryFact)
        finally_facts = [f for f in try_facts if f.has_finally]
        matched = bool(with_facts) or bool(finally_facts)
        ev = {f.fact_id for f in with_facts} | {f.fact_id for f in finally_facts}
        return PredicateResult(matched=matched, confidence="HIGH" if matched else "LOW", signals=("resource_cleanup",) if matched else (), evidence_fact_ids=ev)

    def has_async_for(self, fqn: str) -> PredicateResult:
        facts = self.ast_features.get_facts(fqn, LoopFact)
        afor = [f for f in facts if f.kind == 'async_for']
        matched = bool(afor)
        return PredicateResult(matched=matched, confidence="HIGH" if matched else "LOW", signals=("async_for",) if matched else (), evidence_fact_ids={f.fact_id for f in afor})

    def has_coroutine_calls(self, fqn: str) -> PredicateResult:
        from src.core.models import AsyncFact
        facts = self.ast_features.get_facts(fqn, AsyncFact)
        awaits = [f for f in facts if f.kind == 'await']
        matched = bool(awaits)
        return PredicateResult(matched=matched, confidence="HIGH" if matched else "LOW", signals=("coroutine_calls",) if matched else (), evidence_fact_ids={f.fact_id for f in awaits})

    def has_variable_annotations(self, fqn: str) -> PredicateResult:
        return self.uses_annotated_assignment(fqn)

    def has_parameter_annotations(self, fqn: str) -> PredicateResult:
        from src.core.models import DefinitionFact
        facts = self.ast_features.get_facts(fqn, DefinitionFact)
        defn = [f for f in facts if getattr(f, 'has_param_annotation', False)]
        matched = bool(defn)
        return PredicateResult(matched=matched, confidence="HIGH" if matched else "LOW", signals=("parameter_annotations",) if matched else (), evidence_fact_ids={f.fact_id for f in defn})

    def has_return_annotations(self, fqn: str) -> PredicateResult:
        from src.core.models import DefinitionFact
        facts = self.ast_features.get_facts(fqn, DefinitionFact)
        defn = [f for f in facts if getattr(f, 'has_return_annotation', False)]
        matched = bool(defn)
        return PredicateResult(matched=matched, confidence="HIGH" if matched else "LOW", signals=("return_annotations",) if matched else (), evidence_fact_ids={f.fact_id for f in defn})
        
    def uses_nested_functions(self, fqn: str) -> PredicateResult:
        from src.core.models import DefinitionFact
        facts = self.ast_features.get_facts(fqn, DefinitionFact)
        nested = [f for f in facts if f.definition_type in ("function", "method") and getattr(f.context, "enclosing_function", None)]
        matched = bool(nested)
        return PredicateResult(matched=matched, confidence="HIGH" if matched else "LOW", signals=("nested_function",) if matched else (), evidence_fact_ids={f.fact_id for f in nested})

    def uses_nested_classes(self, fqn: str) -> PredicateResult:
        from src.core.models import DefinitionFact
        facts = self.ast_features.get_facts(fqn, DefinitionFact)
        nested = [f for f in facts if f.definition_type == "class" and getattr(f.context, "enclosing_class", None) or getattr(f.context, "enclosing_function", None)]
        matched = bool(nested)
        return PredicateResult(matched=matched, confidence="HIGH" if matched else "LOW", signals=("nested_class",) if matched else (), evidence_fact_ids={f.fact_id for f in nested})
        
    def uses_properties(self, fqn: str) -> PredicateResult:
        from src.core.models import DecoratorFact
        facts = self.ast_features.get_facts(fqn, DecoratorFact)
        props = [f for f in facts if f.decorator_expression in ("property", "cached_property")]
        matched = bool(props)
        return PredicateResult(matched=matched, confidence="HIGH" if matched else "LOW", signals=("property",) if matched else (), evidence_fact_ids={f.fact_id for f in props})

    def uses_static_methods(self, fqn: str) -> PredicateResult:
        from src.core.models import DecoratorFact
        facts = self.ast_features.get_facts(fqn, DecoratorFact)
        stats = [f for f in facts if f.decorator_expression == "staticmethod"]
        matched = bool(stats)
        return PredicateResult(matched=matched, confidence="HIGH" if matched else "LOW", signals=("staticmethod",) if matched else (), evidence_fact_ids={f.fact_id for f in stats})

    def uses_class_methods(self, fqn: str) -> PredicateResult:
        from src.core.models import DecoratorFact
        facts = self.ast_features.get_facts(fqn, DecoratorFact)
        cls = [f for f in facts if f.decorator_expression == "classmethod"]
        matched = bool(cls)
        return PredicateResult(matched=matched, confidence="HIGH" if matched else "LOW", signals=("classmethod",) if matched else (), evidence_fact_ids={f.fact_id for f in cls})

    def uses_abstract_methods(self, fqn: str) -> PredicateResult:
        from src.core.models import DecoratorFact
        facts = self.ast_features.get_facts(fqn, DecoratorFact)
        abs_meth = [f for f in facts if f.decorator_expression in ("abstractmethod", "abc.abstractmethod")]
        matched = bool(abs_meth)
        return PredicateResult(matched=matched, confidence="HIGH" if matched else "LOW", signals=("abstractmethod",) if matched else (), evidence_fact_ids={f.fact_id for f in abs_meth})

    def uses_tuple_unpacking(self, fqn: str) -> PredicateResult:
        facts = self.ast_features.get_facts(fqn, AssignmentFact)
        unpack = [f for f in facts if f.target_kind == 'TUPLE_UNPACK']
        matched = bool(unpack)
        return PredicateResult(matched=matched, confidence="HIGH" if matched else "LOW", signals=("tuple_unpacking",) if matched else (), evidence_fact_ids={f.fact_id for f in unpack})

    def uses_destructuring(self, fqn: str) -> PredicateResult:
        return self.uses_tuple_unpacking(fqn)

    def uses_env_vars(self, fqn: str) -> PredicateResult:
        calls = self.ast_features.get_facts(fqn, CallFact)
        matched_calls = [
            c for c in calls 
            if (c.func_name in ("getenv", "environ") or (c.receiver == "os" and c.func_name == "getenv") or (c.receiver == "environ"))
        ]
        matched = bool(matched_calls)
        return PredicateResult(
            matched=matched,
            confidence="HIGH" if matched else "LOW",
            signals=("env_vars",) if matched else (),
            evidence_fact_ids={c.fact_id for c in matched_calls}
        )

    def uses_file_reads(self, fqn: str) -> PredicateResult:
        calls = self.ast_features.get_facts(fqn, CallFact)
        matched_calls = [
            c for c in calls
            if c.func_name in ("open", "read", "read_text", "read_bytes", "readline", "readlines")
        ]
        matched = bool(matched_calls)
        return PredicateResult(
            matched=matched,
            confidence="HIGH" if matched else "LOW",
            signals=("file_reads",) if matched else (),
            evidence_fact_ids={c.fact_id for c in matched_calls}
        )

    def uses_file_writes(self, fqn: str) -> PredicateResult:
        calls = self.ast_features.get_facts(fqn, CallFact)
        matched_calls = [
            c for c in calls
            if c.func_name in ("write", "writelines", "write_text", "write_bytes", "flush")
        ]
        matched = bool(matched_calls)
        return PredicateResult(
            matched=matched,
            confidence="HIGH" if matched else "LOW",
            signals=("file_writes",) if matched else (),
            evidence_fact_ids={c.fact_id for c in matched_calls}
        )

    def uses_json(self, fqn: str) -> PredicateResult:
        calls = self.ast_features.get_facts(fqn, CallFact)
        matched_calls = [
            c for c in calls
            if (c.receiver == "json" and c.func_name in ("loads", "dumps", "load", "dump")) or (c.func_name in ("json_loads", "json_dumps"))
        ]
        matched = bool(matched_calls)
        return PredicateResult(
            matched=matched,
            confidence="HIGH" if matched else "LOW",
            signals=("json_serialization",) if matched else (),
            evidence_fact_ids={c.fact_id for c in matched_calls}
        )

    def uses_sockets(self, fqn: str) -> PredicateResult:
        calls = self.ast_features.get_facts(fqn, CallFact)
        matched_calls = [
            c for c in calls
            if (c.receiver == "socket" and c.func_name in ("socket", "create_connection")) or (c.func_name in ("open_connection", "start_server"))
        ]
        matched = bool(matched_calls)
        return PredicateResult(
            matched=matched,
            confidence="HIGH" if matched else "LOW",
            signals=("socket_networking",) if matched else (),
            evidence_fact_ids={c.fact_id for c in matched_calls}
        )

    def uses_logging(self, fqn: str) -> PredicateResult:
        calls = self.ast_features.get_facts(fqn, CallFact)
        matched_calls = [
            c for c in calls
            if c.func_name in ("getLogger", "debug", "info", "warning", "error", "critical", "exception", "log")
        ]
        matched = bool(matched_calls)
        return PredicateResult(
            matched=matched,
            confidence="HIGH" if matched else "LOW",
            signals=("logging",) if matched else (),
            evidence_fact_ids={c.fact_id for c in matched_calls}
        )

    def uses_os(self, fqn: str) -> PredicateResult:
        calls = self.ast_features.get_facts(fqn, CallFact)
        matched_calls = [
            c for c in calls
            if c.receiver in ("os", "path", "sys", "shutil") or c.func_name in ("walk", "listdir", "mkdir", "makedirs", "remove", "rename")
        ]
        matched = bool(matched_calls)
        return PredicateResult(
            matched=matched,
            confidence="HIGH" if matched else "LOW",
            signals=("os_interaction",) if matched else (),
            evidence_fact_ids={c.fact_id for c in matched_calls}
        )


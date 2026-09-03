import ast
import time

from .context import ContextTrackingVisitor
from .models import (
    AssignmentFact,
    AsyncFact,
    CallFact,
    ComprehensionFact,
    ConditionalFact,
    DecoratorFact,
    DefinitionFact,
    GeneratorFact,
    ImportFact,
    InheritanceFact,
    LambdaFact,
    LoopFact,
    RaiseFact,
    ReturnFact,
    TryFact,
    WithFact,
)
from .profiler import profiler


class UnifiedFactVisitor(ContextTrackingVisitor):
    """
    Consolidates fact extraction into a single AST pass.
    """
    def __init__(self, file_path: str, is_test_context: bool = False):
        super().__init__(file_path, is_test_context)
        self.imports: list[ImportFact] = []
        self.calls: list[CallFact] = []
        self.definitions: list[DefinitionFact] = []
        
        self.exceptions: list[TryFact] = []
        self.raises: list[RaiseFact] = []
        self.lambdas: list[LambdaFact] = []
        self.decorators: list[DecoratorFact] = []
        self.asyncs: list[AsyncFact] = []
        self.withs: list[WithFact] = []
        self.loops: list[LoopFact] = []
        self.conditionals: list[ConditionalFact] = []
        self.comprehensions: list[ComprehensionFact] = []
        self.generators: list[GeneratorFact] = []
        
        self.assignments: list[AssignmentFact] = []
        self.inheritances: list[InheritanceFact] = []
        self.returns: list[ReturnFact] = []
        
        self._class_stack: list[str] = []

    def _record_time(self, metric: str, dt: float):
        if metric not in profiler.stats:
            profiler.stats[metric] = 0.0
        profiler.stats[metric] += dt

    # --- Imports ---
    def visit_Import(self, node: ast.Import):
        for alias in node.names:
            t0 = time.time()
            ctx = self.snapshot()
            fact = ImportFact(
                file_path=self.file_path,
                line=node.lineno,
                module=alias.name,
                symbol=None,
                alias=alias.asname,
                context=ctx
            )
            self.imports.append(fact)
            self._record_time("import_fact_creation_seconds", time.time() - t0)
        super().generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom):
        module = node.module if node.module else ""
        for alias in node.names:
            t0 = time.time()
            ctx = self.snapshot()
            fact = ImportFact(
                file_path=self.file_path,
                line=node.lineno,
                module=module,
                symbol=alias.name,
                alias=alias.asname,
                context=ctx
            )
            self.imports.append(fact)
            self._record_time("import_fact_creation_seconds", time.time() - t0)
        super().generic_visit(node)

    # --- Calls ---
    def _qualified_name(self, node):
        if isinstance(node, ast.Name):
            return node.id
        if isinstance(node, ast.Attribute):
            base = self._qualified_name(node.value)
            if base:
                return f"{base}.{node.attr}"
            return node.attr
        if isinstance(node, ast.Call):
            return self._qualified_name(node.func)
        return None

    def visit_Call(self, node: ast.Call):
        func_name = None
        receiver = None

        if isinstance(node.func, ast.Name):
            func_name = node.func.id
        elif isinstance(node.func, ast.Attribute):
            func_name = node.func.attr
            receiver = self._qualified_name(node.func.value)

        if func_name:
            t0 = time.time()
            ctx = self.snapshot()
            fact = CallFact(
                file_path=self.file_path,
                line=node.lineno,
                func_name=func_name,
                receiver=receiver,
                context=ctx
            )
            self.calls.append(fact)
            self._record_time("call_fact_creation_seconds", time.time() - t0)

        super().generic_visit(node)

    # --- Definitions & Decorators ---
    def _extract_decorators(self, node_name: str, node_type: str, decorator_list):
        for dec in decorator_list:
            t0 = time.time()
            ctx = self.snapshot()
            dec_expr = ast.unparse(dec) if hasattr(ast, 'unparse') else "unknown"
            fact = DecoratorFact(
                file_path=self.file_path,
                line=dec.lineno,
                target_name=node_name,
                target_type=node_type,
                decorator_expression=dec_expr,
                context=ctx
            )
            self.decorators.append(fact)
            self._record_time("decorator_fact_creation_seconds", time.time() - t0)

    def visit_ClassDef(self, node: ast.ClassDef):
        qual_name = ".".join(self._class_stack + [node.name])
        
        t0 = time.time()
        ctx = self.snapshot()
        fact = DefinitionFact(
            definition_type="class",
            name=node.name,
            qualified_name=qual_name,
            file_path=self.file_path,
            start_line=node.lineno,
            end_line=getattr(node, 'end_lineno', node.lineno),
            is_async=False,
            context=ctx
        )
        self.definitions.append(fact)
        
        for base in node.bases:
            try:
                base_expr = ast.unparse(base)
            except Exception:
                base_expr = "unknown"
            self.inheritances.append(InheritanceFact(
                file_path=self.file_path,
                line=node.lineno,
                class_name=qual_name,
                base_expression=base_expr,
                context=ctx
            ))
            
        self._record_time("definition_fact_creation_seconds", time.time() - t0)
        
        self._extract_decorators(node.name, "class", node.decorator_list)
        
        self._class_stack.append(node.name)
        super().visit_ClassDef(node)
        self._class_stack.pop()

    def visit_FunctionDef(self, node: ast.FunctionDef):
        self._handle_func(node, False)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
        self._handle_func(node, True)

    def _handle_func(self, node, is_async):
        definition_type = "method" if self._class_stack else "function"
        qual_name = ".".join(self._class_stack + [node.name])
        
        t0 = time.time()
        ctx = self.snapshot()
        has_return_annotation = bool(getattr(node, 'returns', None))
        has_param_annotation = any(getattr(arg, 'annotation', None) for arg in getattr(node.args, 'args', []))

        fact = DefinitionFact(
            definition_type=definition_type,
            name=node.name,
            qualified_name=qual_name,
            file_path=self.file_path,
            start_line=node.lineno,
            end_line=getattr(node, 'end_lineno', node.lineno),
            is_async=is_async,
            has_return_annotation=has_return_annotation,
            has_param_annotation=has_param_annotation,
            context=ctx
        )
        self.definitions.append(fact)
        self._record_time("definition_fact_creation_seconds", time.time() - t0)
        
        self._extract_decorators(node.name, definition_type, node.decorator_list)
        
        if is_async:
            super().visit_AsyncFunctionDef(node)
        else:
            super().visit_FunctionDef(node)

    # --- Exceptions ---
    def _extract_exceptions(self, handlers) -> list[str]:
        caught = []
        for h in handlers:
            if h.type is None:
                caught.append("BaseException") # Bare except
            elif isinstance(h.type, ast.Tuple):
                for elt in h.type.elts:
                    if hasattr(ast, 'unparse'):
                        caught.append(ast.unparse(elt))
            else:
                if hasattr(ast, 'unparse'):
                    caught.append(ast.unparse(h.type))
        return caught

    def visit_Try(self, node: ast.Try):
        t0 = time.time()
        ctx = self.snapshot()
        fact = TryFact(
            file_path=self.file_path,
            line=node.lineno,
            handlers=len(node.handlers),
            has_else=bool(node.orelse),
            has_finally=bool(node.finalbody),
            caught_exceptions=self._extract_exceptions(node.handlers),
            context=ctx
        )
        self.exceptions.append(fact)
        self._record_time("exception_fact_creation_seconds", time.time() - t0)
        
        super().visit_Try(node)
        
    def visit_TryStar(self, node: ast.TryStar):
        # Python 3.11+ ExceptionGroup support
        t0 = time.time()
        ctx = self.snapshot()
        fact = TryFact(
            file_path=self.file_path,
            line=node.lineno,
            handlers=len(node.handlers),
            has_else=bool(node.orelse),
            has_finally=bool(node.finalbody),
            is_star=True,
            caught_exceptions=self._extract_exceptions(node.handlers),
            context=ctx
        )
        self.exceptions.append(fact)
        self._record_time("exception_fact_creation_seconds", time.time() - t0)
        super().visit_TryStar(node)

    def visit_Raise(self, node: ast.Raise):
        t0 = time.time()
        ctx = self.snapshot()
        expr = ast.unparse(node.exc) if node.exc and hasattr(ast, 'unparse') else None
        cause = ast.unparse(node.cause) if node.cause and hasattr(ast, 'unparse') else None
        fact = RaiseFact(
            file_path=self.file_path,
            line=node.lineno,
            exception_expression=expr,
            cause=cause,
            context=ctx
        )
        self.raises.append(fact)
        self._record_time("raise_fact_creation_seconds", time.time() - t0)
        super().generic_visit(node)

    # --- Lambda ---
    def visit_Lambda(self, node: ast.Lambda):
        t0 = time.time()
        ctx = self.snapshot()
        params = [a.arg for a in getattr(node.args, 'args', [])]
        defaults_cnt = len(getattr(node.args, 'defaults', []))
        fact = LambdaFact(
            file_path=self.file_path,
            line=node.lineno,
            parameters=params,
            defaults_count=defaults_cnt,
            context=ctx
        )
        self.lambdas.append(fact)
        self._record_time("lambda_fact_creation_seconds", time.time() - t0)
        super().generic_visit(node)

    # --- Async & With ---
    def visit_Await(self, node: ast.Await):
        t0 = time.time()
        ctx = self.snapshot()
        self.asyncs.append(AsyncFact(self.file_path, node.lineno, "await", context=ctx))
        self._record_time("async_fact_creation_seconds", time.time() - t0)
        super().generic_visit(node)
        
    def _handle_with(self, node, is_async: bool):
        t0 = time.time()
        ctx = self.snapshot()
        fact = WithFact(
            file_path=self.file_path,
            line=node.lineno,
            is_async=is_async,
            items_count=len(node.items),
            context=ctx
        )
        self.withs.append(fact)
        self._record_time("with_fact_creation_seconds", time.time() - t0)
        # ContextTrackingVisitor does not implement visit_With, so we use generic_visit
        super().generic_visit(node)
            
    def visit_With(self, node: ast.With):
        self._handle_with(node, False)
        
    def visit_AsyncWith(self, node: ast.AsyncWith):
        self.asyncs.append(AsyncFact(self.file_path, node.lineno, "async_with", context=self.snapshot()))
        self._handle_with(node, True)

    # --- Loops ---
    def _handle_loop(self, node, kind: str):
        t0 = time.time()
        ctx = self.snapshot()
        # To determine break/continue easily, we'd normally walk the sub-tree, 
        # but for performance we can just check directly if it's feasible, or ignore and just store the loop.
        # It's an O(N) scan to find break/continue. We will skip it for now and assume False, or do a quick walk.
        has_break = any(isinstance(n, ast.Break) for n in ast.walk(node))
        has_continue = any(isinstance(n, ast.Continue) for n in ast.walk(node))
        
        fact = LoopFact(
            file_path=self.file_path,
            line=node.lineno,
            kind=kind,
            has_break=has_break,
            has_continue=has_continue,
            has_else=bool(node.orelse),
            context=ctx
        )
        self.loops.append(fact)
        self._record_time("loop_fact_creation_seconds", time.time() - t0)
        
    def visit_For(self, node: ast.For):
        self._handle_loop(node, "for")
        super().visit_For(node)
        
    def visit_AsyncFor(self, node: ast.AsyncFor):
        self.asyncs.append(AsyncFact(self.file_path, node.lineno, "async_for", context=self.snapshot()))
        self._handle_loop(node, "async_for")
        super().visit_AsyncFor(node)
        
    def visit_While(self, node: ast.While):
        self._handle_loop(node, "while")
        super().visit_While(node)

    # --- Conditionals ---
    def visit_If(self, node: ast.If):
        t0 = time.time()
        ctx = self.snapshot()
        fact = ConditionalFact(self.file_path, node.lineno, "if", branch_count=len(node.orelse)+1, context=ctx)
        self.conditionals.append(fact)
        self._record_time("conditional_fact_creation_seconds", time.time() - t0)
        super().visit_If(node)
        
    def visit_Match(self, node: getattr(ast, 'Match', type("DummyMatch", (), {}))):
        t0 = time.time()
        ctx = self.snapshot()
        fact = ConditionalFact(self.file_path, node.lineno, "match", branch_count=len(node.cases), context=ctx)
        self.conditionals.append(fact)
        self._record_time("conditional_fact_creation_seconds", time.time() - t0)
        super().generic_visit(node)

    # --- Comprehensions ---
    def _handle_comprehension(self, node, kind: str):
        t0 = time.time()
        ctx = self.snapshot()
        gen_cnt = len(node.generators)
        fil_cnt = sum(len(g.ifs) for g in node.generators)
        fact = ComprehensionFact(self.file_path, node.lineno, kind, gen_cnt, fil_cnt, context=ctx)
        self.comprehensions.append(fact)
        self._record_time("comprehension_fact_creation_seconds", time.time() - t0)
        super().generic_visit(node)
        
    def visit_ListComp(self, node: ast.ListComp):
        self._handle_comprehension(node, "list")
        
    def visit_SetComp(self, node: ast.SetComp):
        self._handle_comprehension(node, "set")
        
    def visit_DictComp(self, node: ast.DictComp):
        self._handle_comprehension(node, "dict")
        
    def visit_GeneratorExp(self, node: ast.GeneratorExp):
        self._handle_comprehension(node, "generator")

    # --- Generators ---
    def visit_Yield(self, node: ast.Yield):
        t0 = time.time()
        ctx = self.snapshot()
        self.generators.append(GeneratorFact(self.file_path, node.lineno, "yield", context=ctx))
        self._record_time("generator_fact_creation_seconds", time.time() - t0)
        super().generic_visit(node)
        
    def visit_YieldFrom(self, node: ast.YieldFrom):
        t0 = time.time()
        ctx = self.snapshot()
        self.generators.append(GeneratorFact(self.file_path, node.lineno, "yield_from", context=ctx))
        self._record_time("generator_fact_creation_seconds", time.time() - t0)
        super().generic_visit(node)

    # --- Structural Facts (Assignments, Returns) ---
    def _extract_target_info(self, target: ast.AST):
        if isinstance(target, ast.Name):
            return "NAME", target.id
        elif isinstance(target, ast.Attribute):
            return "ATTRIBUTE", target.attr
        elif isinstance(target, ast.Subscript):
            return "SUBSCRIPT", None
        elif isinstance(target, (ast.Tuple, ast.List)):
            return "TUPLE_UNPACK", None
        return "OTHER", None

    def visit_Assign(self, node: ast.Assign):
        t0 = time.time()
        ctx = self.snapshot()
        rhs_expr = ast.unparse(node.value) if hasattr(ast, 'unparse') and node.value else None
        for target in node.targets:
            kind, name = self._extract_target_info(target)
            self.assignments.append(AssignmentFact(
                file_path=self.file_path,
                line=node.lineno,
                kind="assign",
                target_kind=kind,
                target_name=name,
                has_annotation=False,
                rhs_expression=rhs_expr,
                context=ctx
            ))
        self._record_time("assignment_fact_creation_seconds", time.time() - t0)
        super().generic_visit(node)

    def visit_AnnAssign(self, node: ast.AnnAssign):
        t0 = time.time()
        ctx = self.snapshot()
        kind, name = self._extract_target_info(node.target)
        ann_expr = ast.unparse(node.annotation) if hasattr(ast, 'unparse') and node.annotation else None
        rhs_expr = ast.unparse(node.value) if hasattr(ast, 'unparse') and node.value else None
        self.assignments.append(AssignmentFact(
            file_path=self.file_path,
            line=node.lineno,
            kind="ann_assign",
            target_kind=kind,
            target_name=name,
            has_annotation=True,
            rhs_expression=rhs_expr,
            annotation_expression=ann_expr,
            context=ctx
        ))
        self._record_time("assignment_fact_creation_seconds", time.time() - t0)
        super().generic_visit(node)

    def visit_AugAssign(self, node: ast.AugAssign):
        t0 = time.time()
        ctx = self.snapshot()
        kind, name = self._extract_target_info(node.target)
        self.assignments.append(AssignmentFact(
            file_path=self.file_path,
            line=node.lineno,
            kind="aug_assign",
            target_kind=kind,
            target_name=name,
            has_annotation=False,
            context=ctx
        ))
        self._record_time("assignment_fact_creation_seconds", time.time() - t0)
        super().generic_visit(node)

    def visit_NamedExpr(self, node: ast.NamedExpr):
        t0 = time.time()
        ctx = self.snapshot()
        kind, name = self._extract_target_info(node.target)
        self.assignments.append(AssignmentFact(
            file_path=self.file_path,
            line=node.lineno,
            kind="named_expr",
            target_kind=kind,
            target_name=name,
            has_annotation=False,
            context=ctx
        ))
        self._record_time("assignment_fact_creation_seconds", time.time() - t0)
        super().generic_visit(node)

    def visit_Return(self, node: ast.Return):
        t0 = time.time()
        self.returns.append(ReturnFact(
            file_path=self.file_path,
            line=node.lineno,
            has_value=node.value is not None,
            context=self.snapshot()
        ))
        self._record_time("return_fact_creation_seconds", time.time() - t0)
        super().generic_visit(node)

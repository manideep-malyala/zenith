from src.analysis.predicates.dependency import DependencyPredicates
from src.core.models import AsyncFact
from src.graph.projections.ast_features import ASTFeatureIndex

from .models import PredicateResult


class ConcurrencyPredicates:
    def __init__(self, ast_features: ASTFeatureIndex, dependency: DependencyPredicates):
        self.ast_features = ast_features
        self.dependency = dependency

    def is_async(self, fqn: str) -> PredicateResult:
        async_facts = self.ast_features.get_facts(fqn, AsyncFact)
        matched = bool(async_facts)
        return PredicateResult(
            matched=matched,
            confidence="HIGH" if matched else "LOW",
            signals=("async_await",) if matched else (),
            evidence_fact_ids={f.fact_id for f in async_facts},
            explanation=f"{fqn} contains async/await keywords." if matched else f"{fqn} is not async."
        )

    def uses_thread_pool(self, fqn: str) -> PredicateResult:
        res = self.dependency.depends_on(fqn, "concurrent.futures.ThreadPoolExecutor")
        res2 = self.dependency.depends_on(fqn, "concurrent.futures.thread.ThreadPoolExecutor")
        matched = res.matched or res2.matched
        
        signals = []
        if matched:
            signals.append("thread_pool_executor")
            
        return PredicateResult(
            matched=matched,
            confidence="HIGH" if matched else "LOW",
            signals=tuple(signals),
            evidence_relationship_ids=tuple(set(res.evidence_relationship_ids + res2.evidence_relationship_ids)),
            explanation=f"{fqn} uses ThreadPoolExecutor." if matched else f"{fqn} does not use ThreadPoolExecutor."
        )

    def uses_process_pool(self, fqn: str) -> PredicateResult:
        res = self.dependency.depends_on(fqn, "concurrent.futures.ProcessPoolExecutor")
        res2 = self.dependency.depends_on(fqn, "concurrent.futures.process.ProcessPoolExecutor")
        matched = res.matched or res2.matched
        
        return PredicateResult(
            matched=matched,
            confidence="HIGH" if matched else "LOW",
            signals=("process_pool_executor",) if matched else (),
            evidence_relationship_ids=tuple(set(res.evidence_relationship_ids + res2.evidence_relationship_ids)),
            explanation=f"{fqn} uses ProcessPoolExecutor." if matched else f"{fqn} does not use ProcessPoolExecutor."
        )

    def uses_threading(self, fqn: str) -> PredicateResult:
        res = self.dependency.depends_on(fqn, "threading")
        return PredicateResult(
            matched=res.matched,
            confidence=res.confidence,
            signals=("threading_module",) if res.matched else (),
            evidence_relationship_ids=res.evidence_relationship_ids,
            explanation=f"{fqn} uses the threading module." if res.matched else f"{fqn} does not use the threading module."
        )

    def uses_asyncio(self, fqn: str) -> PredicateResult:
        res = self.dependency.depends_on(fqn, "asyncio")
        return PredicateResult(
            matched=res.matched,
            confidence=res.confidence,
            signals=("asyncio_module",) if res.matched else (),
            evidence_relationship_ids=res.evidence_relationship_ids,
            explanation=f"{fqn} uses the asyncio module." if res.matched else f"{fqn} does not use the asyncio module."
        )

    def uses_locks(self, fqn: str) -> PredicateResult:
        # threading.Lock, threading.RLock, asyncio.Lock, multiprocessing.Lock
        lock_deps = [
            "threading.Lock", "threading.RLock", 
            "asyncio.Lock", "asyncio.locks.Lock",
            "multiprocessing.Lock", "multiprocessing.RLock"
        ]
        return self._check_any_dependency(fqn, lock_deps, "uses_locks", "concurrency locks")

    def uses_queue(self, fqn: str) -> PredicateResult:
        deps = ["queue.Queue", "asyncio.Queue", "multiprocessing.Queue"]
        return self._check_any_dependency(fqn, deps, "uses_queue", "concurrency queues")
        
    def uses_semaphore(self, fqn: str) -> PredicateResult:
        deps = ["threading.Semaphore", "threading.BoundedSemaphore", "asyncio.Semaphore", "asyncio.BoundedSemaphore", "multiprocessing.Semaphore"]
        return self._check_any_dependency(fqn, deps, "uses_semaphore", "semaphores")
        
    def uses_event(self, fqn: str) -> PredicateResult:
        deps = ["threading.Event", "asyncio.Event", "multiprocessing.Event"]
        return self._check_any_dependency(fqn, deps, "uses_event", "concurrency events")
        
    def uses_condition(self, fqn: str) -> PredicateResult:
        deps = ["threading.Condition", "asyncio.Condition", "multiprocessing.Condition"]
        return self._check_any_dependency(fqn, deps, "uses_condition", "condition variables")
        
    def uses_barrier(self, fqn: str) -> PredicateResult:
        deps = ["threading.Barrier", "asyncio.Barrier", "multiprocessing.Barrier"]
        return self._check_any_dependency(fqn, deps, "uses_barrier", "barriers")
        
    def uses_future(self, fqn: str) -> PredicateResult:
        deps = ["concurrent.futures.Future", "asyncio.Future", "asyncio.futures.Future"]
        return self._check_any_dependency(fqn, deps, "uses_future", "futures")

    def uses_thread(self, fqn: str) -> PredicateResult:
        deps = ["threading.Thread"]
        return self._check_any_dependency(fqn, deps, "uses_thread", "threads directly")

    def uses_process(self, fqn: str) -> PredicateResult:
        deps = ["multiprocessing.Process"]
        return self._check_any_dependency(fqn, deps, "uses_process", "processes directly")

    def uses_executor(self, fqn: str) -> PredicateResult:
        res1 = self.uses_thread_pool(fqn)
        res2 = self.uses_process_pool(fqn)
        matched = res1.matched or res2.matched
        signals = []
        if matched:
            signals.append("executor")
        return PredicateResult(
            matched=matched,
            confidence="HIGH" if matched else "LOW",
            signals=tuple(signals),
            evidence_relationship_ids=tuple(set(res1.evidence_relationship_ids) | set(res2.evidence_relationship_ids)),
            explanation=f"{fqn} uses concurrent.futures Executors." if matched else f"{fqn} does not use Executors."
        )

    def uses_submit(self, fqn: str) -> PredicateResult:
        from src.core.models import CallFact
        facts = self.ast_features.get_facts(fqn, CallFact)
        submit_facts = [f for f in facts if f.func_name == 'submit']
        matched = bool(submit_facts)
        return PredicateResult(
            matched=matched,
            confidence="MEDIUM" if matched else "LOW",
            signals=("submit",) if matched else (),
            evidence_fact_ids={f.fact_id for f in submit_facts},
            explanation=f"{fqn} calls submit() (likely on an Executor)." if matched else f"{fqn} does not call submit()."
        )

    def uses_map(self, fqn: str) -> PredicateResult:
        from src.core.models import CallFact
        facts = self.ast_features.get_facts(fqn, CallFact)
        map_facts = [f for f in facts if f.func_name == 'map']
        matched = bool(map_facts)
        return PredicateResult(
            matched=matched,
            confidence="MEDIUM" if matched else "LOW",
            signals=("map",) if matched else (),
            evidence_fact_ids={f.fact_id for f in map_facts},
            explanation=f"{fqn} calls map()." if matched else f"{fqn} does not call map()."
        )

    def uses_as_completed(self, fqn: str) -> PredicateResult:
        from src.core.models import CallFact
        deps = ["concurrent.futures.as_completed"]
        dep_res = self._check_any_dependency(fqn, deps, "as_completed", "concurrent.futures.as_completed")
        
        facts = self.ast_features.get_facts(fqn, CallFact)
        call_facts = [f for f in facts if f.func_name == 'as_completed']
        
        matched = dep_res.matched or bool(call_facts)
        return PredicateResult(
            matched=matched,
            confidence="HIGH" if matched else "LOW",
            signals=("as_completed",) if matched else (),
            evidence_fact_ids={f.fact_id for f in call_facts},
            evidence_relationship_ids=dep_res.evidence_relationship_ids,
            explanation=f"{fqn} uses as_completed()." if matched else f"{fqn} does not use as_completed()."
        )

    def _check_any_dependency(self, fqn: str, targets: list, signal: str, description: str) -> PredicateResult:
        evidence = set()
        for target in targets:
            r = self.dependency.depends_on(fqn, target)
            if r.matched:
                evidence.update(r.evidence_relationship_ids)
                
        matched = bool(evidence)
        return PredicateResult(
            matched=matched,
            confidence="HIGH" if matched else "LOW",
            signals=(signal,) if matched else (),
            evidence_relationship_ids=evidence,
            explanation=f"{fqn} uses {description}." if matched else f"{fqn} does not use {description}."
        )

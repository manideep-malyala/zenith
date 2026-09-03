
from src.analysis.detectors.base import BaseDetector, DetectionContext
from src.analysis.detectors.models import Finding
from src.core.models import Confidence


class StrategyDetector(BaseDetector):
    detector_id = "strategy"
    pattern_name = "Strategy"
    category = "BEHAVIORAL"

    def detect(self, context: DetectionContext) -> list[Finding]:
        findings: list[Finding] = []
        inheritance = context.predicates.inheritance
        dependency = context.predicates.dependency

        # Context -> Strategy
        # Iterate over all local classes as potential Contexts
        all_classes = {
            fqn for fqn, defn in context.registry.definitions_by_fqn.items()
            if defn.definition_type == "class"
        }

        for ctx_class in all_classes:
            deps = dependency.dependencies_of(ctx_class)
            for strategy_candidate in deps:
                # 1. Delegation to strategy (Composition + Calls)
                delegates = dependency.delegates_to_collaborator(ctx_class, strategy_candidate)
                if not delegates.matched:
                    continue

                # We have a basic delegation. Now collect evidence.
                evidence_ids = set(delegates.evidence_relationship_ids)
                signals = ["delegation"]
                related = [strategy_candidate]
                confidence = Confidence.LOW

                # 2. Interchangeable implementations (Inheritance)
                has_subs = inheritance.has_subclasses(strategy_candidate)
                if has_subs.matched:
                    signals.append("interchangeable_implementations")
                    evidence_ids.update(has_subs.evidence_relationship_ids)
                    confidence = Confidence.MEDIUM
                    
                    subs = inheritance.projection.children_of(strategy_candidate)
                    related.extend(subs)

                    # 3. Common behavioral contract (Method overrides)
                    # We check if any subclass overrides methods
                    overrides_found = False
                    for sub in subs:
                        overrides = inheritance.has_method_overrides(sub)
                        if overrides.matched:
                            overrides_found = True
                            evidence_ids.update(overrides.evidence_relationship_ids)
                            break
                            
                    if overrides_found:
                        signals.append("common_behavioral_contract")
                        confidence = Confidence.HIGH

                evidence_ids &= context.valid_relationship_ids
                if not evidence_ids:
                    continue

                explanation = f"{ctx_class} delegates behavior to {strategy_candidate}."
                if "interchangeable_implementations" in signals:
                    explanation += f" {strategy_candidate} has interchangeable implementations."
                if "common_behavioral_contract" in signals:
                    explanation += " Implementations override a common behavioral contract."

                findings.append(Finding(
                    detector_id=self.detector_id,
                    pattern_name=self.pattern_name,
                    category=self.category,
                    subject_fqn=ctx_class,
                    confidence=confidence,
                    finding_type="INFERENCE",
                    evidence_relationship_ids=evidence_ids,
                    explanation=explanation,
                    related_fqns=related,
                ))

        return findings


import yaml

from .capabilities import Answerability, Capability, Operation


class CapabilityRegistry:
    """
    Declarative mapping of concepts to their supported operations and 
    the underlying engine resolver paths (predicates or detectors).
    """
    def __init__(self):
        self._capabilities: dict[str, Capability] = {}

    def load_from_yaml(self, yaml_path: str):
        with open(yaml_path) as f:
            data = yaml.safe_load(f)
            
        for cap_data in data.values():
            operations = [Operation(op) for op in cap_data.get("operations", [])]
            answerability = Answerability(cap_data.get("answerability", "DIRECT"))
            
            cap = Capability(
                concept=cap_data["concept"],
                operations=operations,
                resolver_path=cap_data.get("resolver", "TODO"),
                answerability=answerability,
                description=cap_data.get("description", ""),
                learning_candidate=cap_data.get("learning_candidate", False),
                educational_value=float(cap_data.get("educational_value", 0.5))
            )
            self.register(cap)

    def register(self, capability: Capability):
        self._capabilities[capability.concept] = capability

    def lookup(self, concept: str) -> Capability | None:
        return self._capabilities.get(concept)
        
    def get_all(self) -> list[Capability]:
        return list(self._capabilities.values())

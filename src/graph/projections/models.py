from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .ast_features import ASTFeatureIndex
    from .class_dependency import ClassDependencyProjection
    from .inheritance import InheritanceProjection
    from .module_coupling import ModuleCouplingProjection

@dataclass
class GraphProjections:
    """
    Central container for all deterministic Layer 3 structural graph projections.
    Provides a unified query layer for Layer 4 predicates and Layer 5 detectors.
    """
    class_dependencies: 'ClassDependencyProjection'
    inheritance: 'InheritanceProjection'
    module_coupling: 'ModuleCouplingProjection'
    ast_features: 'ASTFeatureIndex'

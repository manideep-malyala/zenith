# Fixture: Valid Composite pattern
# Component with one Composite child and one Leaf child.

class Graphic:
    """Component base class."""
    def draw(self):
        pass


class CompositeGraphic(Graphic):
    """Composite: inherits AND holds children of type Graphic."""
    def __init__(self):
        self.children = Graphic()  # composes Graphic

    def draw(self):
        pass


class Circle(Graphic):
    """Leaf: inherits Graphic but does not compose it."""
    def draw(self):
        pass

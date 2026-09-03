# Fixture: Negative Composite pattern
# A polymorphic family where NO child composes the base class.
# This should NOT produce a Composite finding.

class Animal:
    """Base class."""
    def speak(self):
        pass


class Dog(Animal):
    """Leaf only — does not compose Animal."""
    def speak(self):
        pass


class Cat(Animal):
    """Leaf only — does not compose Animal."""
    def speak(self):
        pass

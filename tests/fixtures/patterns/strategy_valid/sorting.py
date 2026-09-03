# Fixture: Valid Strategy pattern
# A polymorphic Strategy base with multiple implementations,
# and a Context class that composes the Strategy base.

class SortStrategy:
    """Strategy base class."""
    def sort(self, data):
        raise NotImplementedError


class BubbleSort(SortStrategy):
    """Concrete strategy A."""
    def sort(self, data):
        return sorted(data)


class QuickSort(SortStrategy):
    """Concrete strategy B."""
    def sort(self, data):
        return sorted(data)


class Sorter:
    """Context: composes a SortStrategy."""
    def __init__(self):
        self.strategy = SortStrategy()

    def execute(self, data):
        return self.strategy.sort(data)

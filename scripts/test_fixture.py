import ast
import json
from src.core.extractor import FactExtractor

code = """
# 4 assignments
x = 1
y: int = 2
z += 3
if (w := calculate()):
    pass

# 1 inheritance
class A(Base):
    def m1(self):
        # 1 return
        return 42

class B: # 0 explicit bases in AST (actually bases=[]), so 0 inheritance facts
    pass

class C(A, Mixin): # 2 inheritance facts
    def m2(self):
        # 1 return
        return

async def my_func():
    # 1 return
    return await async_calculate()

"""

tree = ast.parse(code)
extractor = FactExtractor("test_counts.py")
extractor.extract(tree)

print("--- Extracted Counts ---")
print(f"Assignments: {len(extractor.assignments)} (expected 4)")
print(f"Inheritances: {len(extractor.inheritances)} (expected 3)")
print(f"Returns: {len(extractor.returns)} (expected 3)")
print(f"Definitions: {len(extractor.definitions)} (expected 6 - A, m1, B, C, m2, my_func)")

# Let's verify details
for i, f in enumerate(extractor.assignments):
    print(f"Assignment {i}: {f.kind} -> {f.target_name}")

for i, f in enumerate(extractor.inheritances):
    print(f"Inheritance {i}: {f.class_name} inherits {f.base_expression}")

for i, f in enumerate(extractor.returns):
    print(f"Return {i}: has_value={f.has_value}")

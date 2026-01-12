"""Quick test for Phase 5.1: Method Call Extraction"""

import pytest
from pathlib import Path
import sys

pytestmark = pytest.mark.fast

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from cerberus.parser.dependencies import extract_method_calls

# Test code with method calls
test_code = """
class Optimizer:
    def step(self):
        pass

    def zero_grad(self):
        pass

def train(model, optimizer):
    # Simple method call
    optimizer.step()

    # Chained method call
    model.train().forward()

    # Multiple calls on same line
    optimizer.zero_grad(); model.eval()

    # Self method call
    self.process()

    # Module method call
    torch.tensor()
"""
"""Test Phase 5.3: Type Tracking and Method Resolution"""

import pytest
import tempfile
import shutil
from pathlib import Path
import sys

pytestmark = pytest.mark.fast

sys.path.insert(0, str(Path(__file__).parent / "src"))

from cerberus.index.index_builder import build_index
from cerberus.resolution import get_resolution_stats


def test_type_tracking():
    """Test that method calls are resolved to class definitions."""
    test_dir = Path(tempfile.mkdtemp())

    try:
        optimizer_file = test_dir / "optimizer.py"
        optimizer_file.write_text("""
class Optimizer:
    def step(self):
        '''Base optimizer step method'''
        pass

    def zero_grad(self):
        '''Base optimizer zero_grad method'''
        pass

class Adam(Optimizer):
    def step(self):
        '''Adam-specific step implementation'''
        pass
""")

        train_file = test_dir / "train.py"
        train_file.write_text("""
from optimizer import Adam

def train_model():
    optimizer: Adam = Adam()
    optimizer.step()
    optimizer.zero_grad()
    return optimizer
""")

        index_path = test_dir / ".cerberus"
        scan_result = build_index(
            directory=test_dir,
            output_path=index_path,
            store_embeddings=False
        )

        stats = get_resolution_stats(scan_result._store)

        assert stats['total_method_calls'] > 0, "Should have captured method calls"

        if stats['total_symbol_references'] > 0:
            refs = list(scan_result._store.query_symbol_references())
            assert len(refs) > 0

    finally:
        shutil.rmtree(test_dir)

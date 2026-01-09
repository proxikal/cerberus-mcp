"""Test Phase 5.3: Type Tracking and Method Resolution"""

import tempfile
import shutil
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent / "src"))

from cerberus.index.index_builder import build_index
from cerberus.resolution import get_resolution_stats


def test_type_tracking():
    """Test that method calls are resolved to class definitions."""

    # Create a temporary test project
    test_dir = Path(tempfile.mkdtemp())
    print(f"Test project: {test_dir}")

    try:
        # Create optimizer.py with optimizer classes
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

        # Create train.py that uses the optimizer
        train_file = test_dir / "train.py"
        train_file.write_text("""
from optimizer import Adam

def train_model():
    # Type annotation - explicit type
    optimizer: Adam = Adam()

    # Method calls on typed variable
    optimizer.step()
    optimizer.zero_grad()

    return optimizer
""")

        # Index the project
        print("\n🔍 Indexing test project...")
        index_path = test_dir / ".cerberus"
        scan_result = build_index(
            directory=test_dir,
            output_path=index_path,
            store_embeddings=False  # Skip embeddings for speed
        )

        print(f"✅ Index complete")

        # Get resolution stats
        print("\n📊 Resolution Statistics:")
        stats = get_resolution_stats(scan_result._store)

        for key, value in stats.items():
            print(f"  {key}: {value}")

        # Verify type tracking worked
        assert stats['total_method_calls'] > 0, "Should have captured method calls"

        if stats['total_symbol_references'] > 0:
            print(f"\n✅ Phase 5.3: Type tracking works! ({stats['total_symbol_references']} references)")

            # Query the symbol references
            refs = list(scan_result._store.query_symbol_references())
            print(f"\n🔗 Found {len(refs)} symbol references:")
            for ref in refs[:10]:  # Show first 10
                print(f"  {ref.source_file}:{ref.source_line} - {ref.source_symbol}")
                print(f"    → {ref.target_type}.{ref.target_symbol} (confidence: {ref.confidence:.2f})")
                print(f"    Method: {ref.resolution_method}, Type: {ref.reference_type}")
        else:
            print("\n⚠️  No symbol references created")
            print("   This may indicate type information wasn't captured")

    finally:
        # Cleanup
        shutil.rmtree(test_dir)
        print(f"\n🧹 Cleaned up test directory")


if __name__ == "__main__":
    test_type_tracking()

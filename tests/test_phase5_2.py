"""Test Phase 5.2: Import Resolution"""

import pytest
import tempfile
import shutil
from pathlib import Path
import sys

pytestmark = pytest.mark.fast

sys.path.insert(0, str(Path(__file__).parent / "src"))

from cerberus.index.index_builder import build_index
from cerberus.resolution import get_resolution_stats


def test_import_resolution():
    """Test that internal imports are resolved to their definitions."""
    test_dir = Path(tempfile.mkdtemp())

    try:
        utils_file = test_dir / "utils.py"
        utils_file.write_text("""
def helper():
    return "helper result"

class MyClass:
    def method(self):
        pass
""")

        main_file = test_dir / "main.py"
        main_file.write_text("""
from utils import helper, MyClass

def main():
    result = helper()
    obj = MyClass()
    obj.method()
    return result
""")

        index_path = test_dir / ".cerberus"
        scan_result = build_index(
            directory=test_dir,
            output_path=index_path,
            store_embeddings=False
        )

        stats = get_resolution_stats(scan_result._store)

        assert stats['total_import_links'] > 0, "Should have captured import links"

        import_links = list(scan_result._store.query_import_links())
        assert len(import_links) > 0, "Should have import links in database"

    finally:
        shutil.rmtree(test_dir)

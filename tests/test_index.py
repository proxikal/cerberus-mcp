from pathlib import Path

from cerberus.index import build_index, load_index, JSONIndexStore, compute_stats


TEST_FILES_DIR = Path(__file__).parent / "test_files"


def test_build_and_load_index(tmp_path):
    """
    Ensures build_index writes a JSON index and load_index rehydrates it.
    """
    index_path = tmp_path / "index.json"
    scan_result = build_index(TEST_FILES_DIR, index_path, respect_gitignore=False)

    assert index_path.exists()
    loaded = load_index(index_path)

    assert loaded.total_files == scan_result.total_files
    assert {f.path for f in loaded.files} == {f.path for f in scan_result.files}
    assert {s.name for s in loaded.symbols} == {s.name for s in scan_result.symbols}


def test_json_store_round_trip(tmp_path):
    """
    Directly exercises JSONIndexStore for completeness.
    """
    index_path = tmp_path / "store.json"
    store = JSONIndexStore(index_path)
    scan_result = build_index(TEST_FILES_DIR, index_path, respect_gitignore=False)

    reloaded = store.read()
    assert reloaded.total_files == scan_result.total_files
    assert len(reloaded.symbols) == len(scan_result.symbols)


def test_compute_stats(tmp_path):
    """
    Stats should reflect the contents of the index.
    """
    index_path = tmp_path / "stats.json"
    scan_result = build_index(TEST_FILES_DIR, index_path, respect_gitignore=False)

    stats = compute_stats(load_index(index_path))

    assert stats.total_files == scan_result.total_files
    assert stats.total_symbols == len(scan_result.symbols)
    assert stats.symbol_types["class"] >= 3  # At least 3 classes (updated for Phase 5)
    assert stats.symbol_types["function"] >= 7  # At least 7 functions
    assert stats.average_symbols_per_file == len(scan_result.symbols) / scan_result.total_files

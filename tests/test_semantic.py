from pathlib import Path

from cerberus.index import build_index
from cerberus.semantic.search import semantic_search


TEST_FILES_DIR = Path(__file__).parent / "test_files"


def test_semantic_search_returns_ranked_results(tmp_path):
    """
    Lightweight semantic search should surface relevant symbols.
    """
    index_path = tmp_path / "semantic_index.json"
    build_index(TEST_FILES_DIR, index_path, respect_gitignore=False)

    results = semantic_search("greeting with name", index_path, limit=3, padding=1)

    assert results
    names = {r.symbol.name for r in results}
    assert {"greet", "sayHello", "MyTsClass"} & names
    assert results[0].score > 0


def test_semantic_search_no_results(tmp_path):
    """
    Returns empty when nothing matches.
    """
    index_path = tmp_path / "semantic_index.json"
    build_index(TEST_FILES_DIR, index_path, respect_gitignore=False)

    results = semantic_search("quantum flux capacitor", index_path, limit=3, min_score=0.5)
    assert results == []


def test_semantic_search_fallback_mode(tmp_path):
    """
    Fallback token similarity should still return something reasonable without embeddings.
    """
    index_path = tmp_path / "semantic_index.json"
    build_index(TEST_FILES_DIR, index_path, respect_gitignore=False)

    results = semantic_search(
        "greeting",
        index_path,
        limit=2,
        padding=1,
        use_embeddings=False,
        min_score=0.0,
    )
    assert results

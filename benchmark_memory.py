#!/usr/bin/env python3
"""
Memory profiling benchmark for Phase 4 Aegis-Scale validation.

Tests Cerberus indexing and retrieval on large projects to validate
<250 MB constant RAM target for 10,000+ files.

Usage:
    python benchmark_memory.py <project_path> <output_index_dir>
"""

import sys
import time
import tracemalloc
from pathlib import Path
import gc
import json

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from cerberus.index import build_index, load_index
from cerberus.retrieval import hybrid_search


def format_bytes(bytes_value):
    """Format bytes as human-readable string."""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if bytes_value < 1024.0:
            return f"{bytes_value:.2f} {unit}"
        bytes_value /= 1024.0
    return f"{bytes_value:.2f} TB"


def get_memory_stats():
    """Get current memory statistics."""
    current, peak = tracemalloc.get_traced_memory()
    return {
        'current_bytes': current,
        'current': format_bytes(current),
        'peak_bytes': peak,
        'peak': format_bytes(peak),
    }


def benchmark_index_build(project_path: Path, output_path: Path, store_embeddings: bool = False):
    """
    Benchmark index building with memory profiling.

    Args:
        project_path: Path to project to index
        output_path: Path to output SQLite index
        store_embeddings: Whether to generate embeddings

    Returns:
        Dict with benchmark results
    """
    print("\n" + "="*80)
    print("PHASE 4 MEMORY PROFILING: Index Build")
    print("="*80)

    print(f"\nProject: {project_path}")
    print(f"Output: {output_path}")
    print(f"Embeddings: {store_embeddings}")

    # Force garbage collection before starting
    gc.collect()

    # Start memory tracking
    tracemalloc.start()

    # Record baseline
    baseline = get_memory_stats()
    print(f"\nBaseline Memory: {baseline['current']}")

    # Build index
    print("\n" + "-"*80)
    print("Building index...")
    print("-"*80)

    start_time = time.time()

    try:
        result = build_index(
            directory=project_path,
            output_path=output_path,
            respect_gitignore=True,
            extensions=['.py', '.js', '.ts', '.tsx', '.jsx'],  # Common code files
            incremental=False,
            store_embeddings=store_embeddings,
            padding=3,
            model_name="all-MiniLM-L6-v2",
            max_bytes=1_000_000,  # Skip files > 1MB
        )

        elapsed = time.time() - start_time

        # Get peak memory during indexing
        peak_stats = get_memory_stats()

        print(f"\n✓ Index build complete in {elapsed:.2f}s")
        print(f"  Peak Memory: {peak_stats['peak']}")
        print(f"  Current Memory: {peak_stats['current']}")

        # Get index stats
        stats = result._store.get_stats() if hasattr(result, '_store') else {
            'total_files': result.total_files,
            'total_symbols': len(result.symbols),
        }

        print(f"\n  Files Indexed: {stats.get('total_files', 0)}")
        print(f"  Symbols Extracted: {stats.get('total_symbols', 0)}")

        if 'db_size_bytes' in stats:
            print(f"  Database Size: {format_bytes(stats['db_size_bytes'])}")

        # Stop memory tracking
        tracemalloc.stop()

        return {
            'success': True,
            'elapsed_time': elapsed,
            'baseline_memory_bytes': baseline['current_bytes'],
            'peak_memory_bytes': peak_stats['peak_bytes'],
            'current_memory_bytes': peak_stats['current_bytes'],
            'memory_overhead_bytes': peak_stats['peak_bytes'] - baseline['current_bytes'],
            'files_indexed': stats.get('total_files', 0),
            'symbols_extracted': stats.get('total_symbols', 0),
            'db_size_bytes': stats.get('db_size_bytes', 0),
        }

    except Exception as e:
        tracemalloc.stop()
        print(f"\n✗ Index build failed: {e}")
        import traceback
        traceback.print_exc()
        return {
            'success': False,
            'error': str(e),
        }


def benchmark_search(index_path: Path, queries: list):
    """
    Benchmark search operations with memory profiling.

    Args:
        index_path: Path to index
        queries: List of search queries to test

    Returns:
        Dict with benchmark results
    """
    print("\n" + "="*80)
    print("PHASE 4 MEMORY PROFILING: Search Operations")
    print("="*80)

    print(f"\nIndex: {index_path}")
    print(f"Queries: {len(queries)}")

    # Force garbage collection
    gc.collect()

    # Start memory tracking
    tracemalloc.start()

    # Record baseline
    baseline = get_memory_stats()
    print(f"\nBaseline Memory: {baseline['current']}")

    results = []

    for i, query in enumerate(queries, 1):
        print(f"\n{'-'*80}")
        print(f"Query {i}/{len(queries)}: '{query}'")
        print('-'*80)

        start_time = time.time()

        try:
            search_results = hybrid_search(
                query=query,
                index_path=index_path,
                mode="balanced",
                top_k=10,
            )

            elapsed = time.time() - start_time
            current_stats = get_memory_stats()

            print(f"  ✓ Found {len(search_results)} results in {elapsed:.2f}s")
            print(f"  Memory: {current_stats['current']} (peak: {current_stats['peak']})")

            if search_results:
                print(f"  Top result: {search_results[0].symbol.name} (score: {search_results[0].hybrid_score:.3f})")

            results.append({
                'query': query,
                'success': True,
                'elapsed_time': elapsed,
                'result_count': len(search_results),
                'peak_memory_bytes': current_stats['peak_bytes'],
            })

        except Exception as e:
            print(f"  ✗ Search failed: {e}")
            results.append({
                'query': query,
                'success': False,
                'error': str(e),
            })

    # Final stats
    final_stats = get_memory_stats()

    print(f"\n{'='*80}")
    print("SEARCH SUMMARY")
    print('='*80)
    print(f"Baseline Memory: {baseline['current']}")
    print(f"Peak Memory: {final_stats['peak']}")
    print(f"Final Memory: {final_stats['current']}")
    print(f"Memory Growth: {format_bytes(final_stats['current_bytes'] - baseline['current_bytes'])}")

    tracemalloc.stop()

    return {
        'queries': results,
        'baseline_memory_bytes': baseline['current_bytes'],
        'peak_memory_bytes': final_stats['peak_bytes'],
        'final_memory_bytes': final_stats['current_bytes'],
        'memory_growth_bytes': final_stats['current_bytes'] - baseline['current_bytes'],
    }


def main():
    if len(sys.argv) < 3:
        print("Usage: python benchmark_memory.py <project_path> <output_index_dir>")
        print("\nExample:")
        print("  python benchmark_memory.py ./tests/tensorflow_test ./test_index")
        sys.exit(1)

    project_path = Path(sys.argv[1])
    output_path = Path(sys.argv[2])

    if not project_path.exists():
        print(f"Error: Project path does not exist: {project_path}")
        sys.exit(1)

    print("\n" + "="*80)
    print("CERBERUS PHASE 4 AEGIS-SCALE MEMORY BENCHMARK")
    print("="*80)
    print("\nTarget: <250 MB constant RAM for 10,000+ files")
    print("Test: TensorFlow repository (massive codebase)")

    # Benchmark 1: Index build (no embeddings for speed)
    index_result = benchmark_index_build(
        project_path=project_path,
        output_path=output_path,
        store_embeddings=False,  # Faster for large projects
    )

    if not index_result['success']:
        print("\n✗ Index build failed, aborting benchmark")
        sys.exit(1)

    # Benchmark 2: Search operations
    test_queries = [
        "tensorflow optimizer",
        "neural network layer",
        "gradient computation",
        "loss function",
        "model training",
    ]

    search_result = benchmark_search(
        index_path=output_path,
        queries=test_queries,
    )

    # Generate final report
    print("\n" + "="*80)
    print("PHASE 4 VALIDATION REPORT")
    print("="*80)

    print("\n--- INDEX BUILD ---")
    print(f"Files Indexed: {index_result['files_indexed']:,}")
    print(f"Symbols Extracted: {index_result['symbols_extracted']:,}")
    print(f"Build Time: {index_result['elapsed_time']:.2f}s")
    print(f"Peak Memory: {format_bytes(index_result['peak_memory_bytes'])}")
    print(f"Memory Overhead: {format_bytes(index_result['memory_overhead_bytes'])}")
    print(f"Database Size: {format_bytes(index_result['db_size_bytes'])}")

    print("\n--- SEARCH OPERATIONS ---")
    successful_searches = sum(1 for q in search_result['queries'] if q['success'])
    avg_search_time = sum(q.get('elapsed_time', 0) for q in search_result['queries'] if q['success']) / max(successful_searches, 1)

    print(f"Queries Executed: {len(search_result['queries'])}")
    print(f"Successful: {successful_searches}")
    print(f"Average Search Time: {avg_search_time:.2f}s")
    print(f"Peak Memory: {format_bytes(search_result['peak_memory_bytes'])}")
    print(f"Memory Growth: {format_bytes(search_result['memory_growth_bytes'])}")

    print("\n--- VALIDATION ---")
    target_memory = 250 * 1024 * 1024  # 250 MB in bytes
    peak_memory = max(index_result['peak_memory_bytes'], search_result['peak_memory_bytes'])

    if peak_memory < target_memory:
        print(f"✓ PASS: Peak memory {format_bytes(peak_memory)} < 250 MB target")
        print("✓ Phase 4 Aegis-Scale memory target achieved!")
    else:
        print(f"✗ FAIL: Peak memory {format_bytes(peak_memory)} > 250 MB target")
        print(f"  Exceeded by: {format_bytes(peak_memory - target_memory)}")

    # Save detailed results
    report_path = output_path.parent / "benchmark_report.json"
    with open(report_path, 'w') as f:
        json.dump({
            'index_build': index_result,
            'search': search_result,
            'validation': {
                'target_memory_bytes': target_memory,
                'peak_memory_bytes': peak_memory,
                'passed': peak_memory < target_memory,
            }
        }, f, indent=2)

    print(f"\nDetailed report saved to: {report_path}")
    print("\n" + "="*80)


if __name__ == '__main__':
    main()

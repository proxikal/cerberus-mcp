from collections import Counter
from cerberus.schemas import IndexStats, ScanResult


def compute_stats(scan_result: ScanResult) -> IndexStats:
    """
    Compute basic statistics from a ScanResult to keep outputs concise.
    """
    total_files = scan_result.total_files
    total_symbols = len(scan_result.symbols)

    type_counts = Counter(symbol.type for symbol in scan_result.symbols)
    avg_per_file = total_symbols / total_files if total_files else 0.0

    return IndexStats(
        total_files=total_files,
        total_symbols=total_symbols,
        symbol_types=dict(type_counts),
        average_symbols_per_file=avg_per_file,
    )

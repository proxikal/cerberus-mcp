"""
Phase 9.5: Thin Client Routing Helper for Retrieval Commands.

Provides wrapper functions that route through daemon when available.
"""

from pathlib import Path
from typing import List, Optional
from loguru import logger

from cerberus.schemas import CodeSymbol
from cerberus.daemon import is_daemon_available, route_get_symbol
from cerberus.index import load_index, find_symbol


def get_symbol_with_routing(
    name: str,
    index_path: Path,
    use_daemon: bool = True,
) -> List[CodeSymbol]:
    """
    Get symbol with automatic daemon routing.

    Args:
        name: Symbol name
        index_path: Path to index
        use_daemon: Enable daemon routing (default: True)

    Returns:
        List of matching CodeSymbol objects

    Phase 9.5: Smart routing with transparent fallback
    """
    # Try daemon first if available and enabled
    if use_daemon and is_daemon_available():
        try:
            logger.info(f"Phase 9.5: Routing get-symbol '{name}' through daemon")
            result = route_get_symbol(name=name, index_path=index_path, file_filter=None)

            if result and result.get("found"):
                # Convert daemon response to CodeSymbol objects
                matches = []
                for match_data in result.get("matches", []):
                    match_obj = CodeSymbol(
                        name=match_data.get("name"),
                        type=match_data.get("type") or "function",
                        file_path=match_data.get("file"),
                        start_line=match_data.get("line_start") or 0,
                        end_line=match_data.get("line_end") or 0,
                        signature=match_data.get("signature"),
                        parent_class=match_data.get("parent_class"),
                    )
                    matches.append(match_obj)
                logger.debug(f"Daemon returned {len(matches)} matches")
                return matches
            else:
                logger.debug(f"Daemon found no matches")
                return []
        except Exception as e:
            logger.debug(f"Daemon routing failed: {e}, falling back to direct execution")
            # Fall through to direct execution

    # Direct execution (daemon unavailable or disabled or failed)
    logger.info(f"Phase 9.5: Using direct execution for get-symbol '{name}'")
    scan_result = load_index(index_path)
    return find_symbol(name, scan_result)

"""Synthesis tools for skeletonization and context building."""
from typing import Optional, List
from pathlib import Path

from cerberus.synthesis.skeletonizer import Skeletonizer
from cerberus.synthesis.facade import get_synthesis_facade


def register(mcp):
    @mcp.tool()
    def skeletonize(
        path: str,
        preserve_symbols: Optional[List[str]] = None,
        format: str = "code"
    ) -> dict:
        """
        Generate code skeleton - signatures and structure without implementation.

        Removes function/method bodies while preserving:
        - Class/function signatures
        - Type annotations
        - Docstrings (first line only)
        - Import statements

        Token savings: typically 70-90% reduction vs full file.

        Args:
            path: File path to skeletonize
            preserve_symbols: Symbol names to keep full implementation (not skeletonize)
            format: Output format - "code" (skeleton source), "json" (structured)

        Returns:
            Skeletonized code with compression stats
        """
        file_path = Path(path).resolve()

        if not file_path.exists():
            return {"error": f"File not found: {path}"}

        if not file_path.is_file():
            return {"error": f"Path is not a file: {path}"}

        try:
            skeletonizer = Skeletonizer()
            result = skeletonizer.skeletonize_file(str(file_path), preserve_symbols)

            if format == "json":
                return {
                    "file_path": result.file_path,
                    "original_lines": result.original_lines,
                    "skeleton_lines": result.skeleton_lines,
                    "compression_ratio": result.compression_ratio,
                    "preserved_symbols": result.preserved_symbols,
                    "pruned_symbols": result.pruned_symbols,
                    "content": result.content
                }
            else:
                # Return code format with header comment
                header = f"# Skeleton: {result.file_path}\n"
                header += f"# Lines: {result.skeleton_lines}/{result.original_lines} "
                header += f"({result.compression_ratio:.1%} of original)\n\n"
                return {
                    "skeleton": header + result.content,
                    "stats": {
                        "original_lines": result.original_lines,
                        "skeleton_lines": result.skeleton_lines,
                        "compression_ratio": result.compression_ratio,
                        "tokens_saved_estimate": int(result.original_lines * 10 * (1 - result.compression_ratio))
                    }
                }
        except Exception as e:
            return {"error": str(e)}

    @mcp.tool()
    def skeletonize_directory(
        path: str = ".",
        pattern: str = "**/*.py"
    ) -> dict:
        """
        Get a summary of all skeletonizable files in a directory.

        **AI WORKFLOW:**
        1. Use this tool to survey a directory/module
        2. Review the file list and identify relevant files
        3. Call skeletonize() on specific files you need

        **DO NOT** try to get all file contents at once - work file-by-file
        for token efficiency and context control.

        Args:
            path: Directory path to scan
            pattern: Glob pattern for files (default: **/*.py)

        Returns:
            Summary with file list, compression stats, and token savings estimate.
            Use the file paths to selectively call skeletonize() on specific files.
        """
        dir_path = Path(path).resolve()

        if not dir_path.exists():
            return {"error": f"Directory not found: {path}"}

        if not dir_path.is_dir():
            return {"error": f"Path is not a directory: {path}"}

        try:
            facade = get_synthesis_facade()
            results = facade.skeletonize_directory(str(dir_path), pattern)

            if not results:
                return {"error": f"No files matched pattern: {pattern}"}

            total_original = sum(r.original_lines for r in results)
            total_skeleton = sum(r.skeleton_lines for r in results)
            overall_ratio = total_skeleton / total_original if total_original > 0 else 0

            return {
                "files_found": len(results),
                "total_original_lines": total_original,
                "total_skeleton_lines": total_skeleton,
                "overall_compression": overall_ratio,
                "tokens_saved_estimate": int(total_original * 10 * (1 - overall_ratio)),
                "files": [
                    {
                        "path": r.file_path,
                        "lines": f"{r.skeleton_lines}/{r.original_lines}",
                        "compression": f"{r.compression_ratio:.1%}"
                    }
                    for r in results
                ],
                "next_step": "Call skeletonize(path) on specific files from the list above"
            }
        except Exception as e:
            return {"error": str(e)}

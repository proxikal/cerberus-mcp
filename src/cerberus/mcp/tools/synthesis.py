"""Synthesis tools for skeletonization and context building."""
from typing import Optional, List, Dict, Any
from pathlib import Path

from cerberus.synthesis.skeletonizer import Skeletonizer
from cerberus.synthesis.facade import get_synthesis_facade
from cerberus.mcp.config import get_config_value


def register(mcp):
    @mcp.tool()
    def skeletonize(
        path: Optional[str] = None,
        preserve_symbols: Optional[List[str]] = None,
        format: str = "code",
        files: Optional[List[str]] = None,
    ) -> dict:
        """Generate code skeleton without implementation bodies."""
        # Validate inputs
        if not path and not files:
            return {"error": "Must provide either path for single file or files for bulk skeletonization"}

        # Handle bulk mode
        if files:
            # Check bulk limit
            max_files = get_config_value("limits.bulk_skeletonize_max_files", 20)
            if len(files) > max_files:
                return {
                    "error": f"Requested {len(files)} files, exceeds bulk skeletonize limit of {max_files}. "
                            f"Reduce request size or adjust 'limits.bulk_skeletonize_max_files' in config."
                }

            all_results: list = []
            errors: list = []
            total_original_lines = 0
            total_skeleton_lines = 0
            skeletonizer = Skeletonizer()

            for idx, file_path_str in enumerate(files):
                try:
                    file_path = Path(file_path_str).resolve()

                    if not file_path.exists():
                        errors.append(f"{file_path_str}: File not found")
                        continue

                    if not file_path.is_file():
                        errors.append(f"{file_path_str}: Not a file")
                        continue

                    result = skeletonizer.skeletonize_file(str(file_path), preserve_symbols)

                    total_original_lines += result.original_lines
                    total_skeleton_lines += result.skeleton_lines

                    if format == "json":
                        all_results.append({
                            "file_path": result.file_path,
                            "original_lines": result.original_lines,
                            "skeleton_lines": result.skeleton_lines,
                            "compression_ratio": result.compression_ratio,
                            "content": result.content
                        })
                    else:
                        header = f"# Skeleton: {result.file_path}\n"
                        header += f"# Lines: {result.skeleton_lines}/{result.original_lines} "
                        header += f"({result.compression_ratio:.1%} of original)\n\n"
                        all_results.append({
                            "file_path": result.file_path,
                            "skeleton": header + result.content,
                            "stats": {
                                "original_lines": result.original_lines,
                                "skeleton_lines": result.skeleton_lines,
                                "compression_ratio": result.compression_ratio
                            }
                        })

                except Exception as e:
                    errors.append(f"{file_path_str}: {str(e)}")

            # Calculate overall stats
            overall_compression = total_skeleton_lines / total_original_lines if total_original_lines > 0 else 0

            return {
                "bulk_mode": True,
                "requested_count": len(files),
                "success_count": len(all_results),
                "error_count": len(errors),
                "results": all_results,
                "overall_stats": {
                    "total_original_lines": total_original_lines,
                    "total_skeleton_lines": total_skeleton_lines,
                    "overall_compression": overall_compression,
                    "tokens_saved_estimate": int(total_original_lines * 10 * (1 - overall_compression))
                },
                "errors": errors if errors else None
            }

        # Single mode (original logic)
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
        """Get summary of skeletonizable files in directory."""
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

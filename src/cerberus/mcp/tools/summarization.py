"""Summarization tools using local LLM."""
from typing import Optional, List
from pathlib import Path

from cerberus.summarization.facade import get_summarization_facade


def register(mcp):
    @mcp.tool()
    def summarize(
        path: str,
        focus: Optional[str] = None
    ) -> dict:
        """
        Generate AI-powered summary of a file.

        Uses local LLM (Ollama) to create concise summary including:
        - Purpose and functionality
        - Key components and patterns
        - Dependencies and complexity

        Requires: Ollama running locally with configured model.

        Args:
            path: File path to summarize
            focus: Optional focus area (e.g., "error handling", "data flow")

        Returns:
            Summary with purpose, key points, and complexity score
        """
        file_path = Path(path).resolve()

        if not file_path.exists():
            return {"error": f"File not found: {path}"}

        if not file_path.is_file():
            return {"error": f"Path is not a file: {path}"}

        try:
            facade = get_summarization_facade()

            # Check LLM availability
            if not facade.llm_client.is_available():
                return {
                    "error": "Local LLM not available",
                    "hint": "Ensure Ollama is running: ollama serve"
                }

            result = facade.summarize_file(str(file_path), focus)

            if not result:
                return {"error": "Failed to generate summary"}

            return {
                "target": result.target,
                "type": result.summary_type,
                "summary": result.summary_text,
                "key_points": result.key_points,
                "dependencies": result.dependencies,
                "complexity": result.complexity_score,
                "model": result.model_used
            }
        except Exception as e:
            return {"error": str(e)}

    @mcp.tool()
    def summarize_architecture(
        name: str,
        paths: List[str]
    ) -> dict:
        """
        Summarize an architectural subsystem or module.

        Analyzes multiple files together to understand their collective
        purpose and relationships. Useful for understanding layers,
        packages, or feature modules.

        Requires: Ollama running locally.

        Args:
            name: Name of the subsystem (e.g., "authentication", "data layer")
            paths: List of file paths in this subsystem

        Returns:
            Architectural summary with patterns and relationships
        """
        if not paths:
            return {"error": "No paths provided"}

        # Validate paths
        valid_files = []
        for p in paths:
            file_path = Path(p).resolve()
            if file_path.exists() and file_path.is_file():
                valid_files.append(str(file_path))

        if not valid_files:
            return {"error": "No valid files found in provided paths"}

        try:
            facade = get_summarization_facade()

            if not facade.llm_client.is_available():
                return {
                    "error": "Local LLM not available",
                    "hint": "Ensure Ollama is running: ollama serve"
                }

            result = facade.summarize_architecture(name, valid_files)

            if not result:
                return {"error": "Failed to generate architecture summary"}

            return {
                "target": result.target,
                "type": result.summary_type,
                "summary": result.summary_text,
                "key_points": result.key_points,
                "dependencies": result.dependencies,
                "complexity": result.complexity_score,
                "files_analyzed": len(valid_files),
                "model": result.model_used
            }
        except Exception as e:
            return {"error": str(e)}

    @mcp.tool()
    def summarize_status() -> dict:
        """
        Check summarization service status.

        Verifies if local LLM is available and configured.

        Returns:
            Status info including model and availability
        """
        try:
            facade = get_summarization_facade()
            available = facade.llm_client.is_available()

            return {
                "available": available,
                "model": facade.llm_client.config.get("model", "unknown"),
                "endpoint": facade.llm_client.config.get("ollama_url", "unknown"),
                "hint": None if available else "Start Ollama: ollama serve"
            }
        except Exception as e:
            return {
                "available": False,
                "error": str(e)
            }

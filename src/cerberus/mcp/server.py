"""FastMCP server setup and tool registration."""
from fastmcp import FastMCP

from .tools import (
    analysis,
    analysis_tools,
    context,
    diagnostics,
    indexing,
    memory,
    metrics,
    quality,
    reading,
    search,
    structure,
    summarization,
    symbols,
    synthesis,
)

mcp = FastMCP("cerberus")


def create_server():
    """Create and configure the MCP server."""
    # Read tools
    search.register(mcp)
    symbols.register(mcp)
    reading.register(mcp)
    structure.register(mcp)

    # Synthesis tools (skeletonization, context building)
    synthesis.register(mcp)

    # Context assembly (power tool - replaces multi-tool workflows)
    context.register(mcp)

    # Summarization tools (LLM-powered)
    summarization.register(mcp)

    # Analysis tools (call graphs, dependencies)
    analysis.register(mcp)

    # Advanced analysis tools (project summary, impact analysis, test coverage)
    analysis_tools.register(mcp)

    # Index management
    indexing.register(mcp)

    # Memory system
    memory.register(mcp)

    # Quality & metrics
    quality.register(mcp)
    metrics.register(mcp)

    # Diagnostics
    diagnostics.register(mcp)

    return mcp


def run_server():
    """Run the MCP server."""
    server = create_server()
    server.run(show_banner=False)

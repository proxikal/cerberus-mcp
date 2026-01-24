"""Summary formatter for activation summaries."""
from typing import Dict, Any, Optional
from .templates import TEMPLATES, DEFAULT_TEMPLATE


def format_activation_summary(
    health_data: Dict[str, Any],
    memory_context: Optional[str] = None,
    template: Optional[str] = None,
) -> str:
    """
    Format activation summary using specified template.

    Args:
        health_data: Data from health_check() tool
        memory_context: String context from memory_context() tool
        template: Template name (professional, minimal, dashboard, modern, terminal)
                  If None or invalid, defaults to 'modern'

    Returns:
        Formatted summary string
    """
    # Validate template
    template_name = template or DEFAULT_TEMPLATE
    if template_name not in TEMPLATES:
        template_name = DEFAULT_TEMPLATE

    # Extract key context from memory_context string if provided
    key_context = []
    if memory_context:
        key_context = _extract_key_context(memory_context)

    # Prepare data for template
    data = {
        **health_data,
        "key_context": key_context,
        "project": _extract_project_name(memory_context) if memory_context else "unknown",
    }

    # Get template function and format
    formatter = TEMPLATES[template_name]
    return formatter(data)


def _extract_key_context(memory_context: str, max_items: int = 3) -> list:
    """
    Extract key context items from memory_context string.

    Extracts recent/important decisions and preferences.

    Args:
        memory_context: Raw memory context string
        max_items: Maximum number of items to extract

    Returns:
        List of key context strings
    """
    key_items = []

    # Split into lines
    lines = memory_context.split("\n")

    # Look for decision and preference lines
    for line in lines:
        if line.startswith("decision:") or line.startswith("pref:") or line.startswith("rule:"):
            # Extract the content after the prefix
            parts = line.split(":", 1)
            if len(parts) > 1:
                content = parts[1].strip()
                # Clean up the content
                if "[" in content:
                    # Remove project tag at end like [cerberus]
                    content = content.split("[")[0].strip()
                # Replace underscores with spaces for readability
                content = content.replace("_", " ").capitalize()
                key_items.append(content)

        if len(key_items) >= max_items:
            break

    return key_items


def _extract_project_name(memory_context: str) -> str:
    """
    Extract project name from memory context.

    Args:
        memory_context: Raw memory context string

    Returns:
        Project name or "unknown"
    """
    # Look for project marker like "*project:cerberus*"
    for line in memory_context.split("\n"):
        if line.startswith("*project:") or line.startswith("*Project:"):
            # Extract project name
            parts = line.split(":", 1)
            if len(parts) > 1:
                project = parts[1].strip().rstrip("*")
                return project

    # Look for scope line like "scope:project:cerberus"
    for line in memory_context.split("\n"):
        if line.startswith("scope:project:"):
            parts = line.split(":", 2)
            if len(parts) > 2:
                return parts[2].strip()

    return "unknown"

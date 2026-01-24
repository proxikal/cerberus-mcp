"""Activation summary templates for CerberusBeta skill."""
from typing import Dict, Any


def format_box(data: Dict[str, Any]) -> str:
    """
    Option 1: Box Style (Professional)

    Args:
        data: Summary data from health_check and memory_context

    Returns:
        Formatted summary string
    """
    ctx = data["context"]
    version = data["version"]
    index_status = "✓ healthy" if data.get("index_available") else "✗ unavailable"
    index_age = f"({data['index'].get('age_hours', 0)}h old)" if data.get("index_available") else ""
    memory_total = data["memory"].get("total", 0)
    mem_prefs = data["memory"].get("preferences", 0)
    mem_decs = data["memory"].get("decisions", 0)
    mem_corrs = data["memory"].get("corrections", 0)

    # Get key context (top 3 items from memory)
    key_context = data.get("key_context", [])

    # Get capabilities
    caps = data.get("capabilities", [])
    caps_line1 = " • ".join(caps[:4]) if len(caps) > 4 else " • ".join(caps)
    caps_line2 = " • ".join(caps[4:8]) if len(caps) > 4 else ""

    lines = [
        "╔══════════════════════════════════════════════════════════════╗",
        "║                  CERBERUS BETA ACTIVE                        ║",
        "╠══════════════════════════════════════════════════════════════╣",
        f"║ Context: {ctx:<24} Version: {version:<13}║",
        f"║ Index: {index_status} {index_age:<17} Memory: {memory_total} entries{' '*(5-len(str(memory_total)))}║",
        "╠══════════════════════════════════════════════════════════════╣",
        "║ MEMORY CONTEXT                                               ║",
        f"║   Preferences....... {mem_prefs} active{' '*(31-len(str(mem_prefs)))}║",
        f"║   Decisions......... {mem_decs} recorded{' '*(28-len(str(mem_decs)))}║",
        f"║   Corrections....... {mem_corrs} applied{' '*(28-len(str(mem_corrs)))}║",
        "║                                                              ║",
    ]

    if key_context:
        lines.append("║ KEY CONTEXT                                                  ║")
        for item in key_context[:3]:
            # Truncate to fit in box
            item_text = item[:58] + "..." if len(item) > 58 else item
            padding = 62 - len(item_text) - 5
            lines.append(f"║   • {item_text}{' ' * padding}║")
        lines.append("║                                                              ║")

    lines.append("║ CAPABILITIES                                                 ║")
    lines.append(f"║   {caps_line1:<60}║")
    if caps_line2:
        lines.append(f"║   {caps_line2:<60}║")

    lines.extend([
        "╠══════════════════════════════════════════════════════════════╣",
        "║ 🎯 Ready for optimized navigation                            ║",
        "╚══════════════════════════════════════════════════════════════╝"
    ])

    return "\n".join(lines)


def format_minimal(data: Dict[str, Any]) -> str:
    """
    Option 2: Minimal (Clean & Compact)

    Args:
        data: Summary data from health_check and memory_context

    Returns:
        Formatted summary string
    """
    ctx = data["context"]
    version = data["version"]
    project = data.get("project", "unknown")
    index_status = "✓ healthy" if data.get("index_available") else "✗ unavailable"
    index_age = f"({data['index'].get('age_hours', 0)}h)" if data.get("index_available") else ""
    memory_total = data["memory"].get("total", 0)
    mem_prefs = data["memory"].get("preferences", 0)
    mem_decs = data["memory"].get("decisions", 0)
    mem_corrs = data["memory"].get("corrections", 0)

    key_context = data.get("key_context", [])

    lines = [
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
        f" CERBERUS BETA • v{version} • {ctx}:{project}",
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
        "",
        f"Index    {index_status} {index_age}",
        f"Memory   {memory_total} entries ({mem_prefs} prefs, {mem_decs} decisions, {mem_corrs} corrections)",
        "",
    ]

    if key_context:
        lines.append("Context")
        for item in key_context[:3]:
            lines.append(f"  → {item}")
        lines.append("")

    lines.extend([
        "Ready • All capabilities online",
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    ])

    return "\n".join(lines)


def format_dashboard(data: Dict[str, Any]) -> str:
    """
    Option 3: Dashboard Style (Information Dense)

    Args:
        data: Summary data from health_check and memory_context

    Returns:
        Formatted summary string
    """
    ctx = data["context"]
    version = data["version"]
    py_version = data.get("python_version", "unknown")
    index_status = "✓" if data.get("index_available") else "✗"
    index_age = f"{data['index'].get('age_hours', 0)}h" if data.get("index_available") else "N/A"
    mem_prefs = data["memory"].get("preferences", 0)
    mem_decs = data["memory"].get("decisions", 0)
    mem_corrs = data["memory"].get("corrections", 0)
    mem_projects = data["memory"].get("decision_projects", 0)

    caps = data.get("capabilities", [])
    caps_line1 = " │ ".join(caps[:4])
    caps_line2 = " │ ".join(caps[4:8]) if len(caps) > 4 else ""
    caps_line3 = " │ ".join(caps[8:]) if len(caps) > 8 else ""

    key_context = data.get("key_context", [])

    lines = [
        "┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓",
        "┃ 🐺 CERBERUS BETA ONLINE                                      ┃",
        "┣━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┫",
        "┃                                                              ┃",
        f"┃  SYSTEM STATUS                   MEMORY LOADED               ┃",
        f"┃  ├─ Context........ {ctx:<10}├─ Preferences..... {mem_prefs:<6}┃",
        f"┃  ├─ Version........ {version:<10}├─ Decisions....... {mem_decs:<6}┃",
        f"┃  ├─ Index.......... {index_status} {index_age:<8}├─ Corrections..... {mem_corrs:<6}┃",
        f"┃  └─ Python......... {py_version:<10}└─ Projects........ {mem_projects:<6}┃",
        "┃                                                              ┃",
        "┃  ACTIVE CAPABILITIES                                         ┃",
        f"┃  {caps_line1:<60}┃",
    ]

    if caps_line2:
        lines.append(f"┃  {caps_line2:<60}┃")
    if caps_line3:
        lines.append(f"┃  {caps_line3:<60}┃")

    lines.append("┃                                                              ┃")

    if key_context:
        lines.append("┃  SESSION CONTEXT                                             ┃")
        for item in key_context[:3]:
            item_text = item[:58] + "..." if len(item) > 58 else item
            padding = 62 - len(item_text) - 5
            lines.append(f"┃  • {item_text}{' ' * padding}┃")
        lines.append("┃                                                              ┃")

    lines.extend([
        "┣━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┫",
        "┃ ⚡ Token-optimized navigation ready                          ┃",
        "┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛"
    ])

    return "\n".join(lines)


def format_modern(data: Dict[str, Any]) -> str:
    """
    Option 4: Badge/Tag Style (Modern) - DEFAULT

    Args:
        data: Summary data from health_check and memory_context

    Returns:
        Formatted summary string
    """
    ctx = data["context"]
    version = data["version"]
    py_version = data.get("python_version", "unknown")
    status = "✓ healthy" if data.get("index_available") else "⚠ no index"
    index_age = f"{data['index'].get('age_hours', 0)}h old" if data.get("index_available") else "N/A"
    memory_total = data["memory"].get("total", 0)
    mem_prefs = data["memory"].get("preferences", 0)
    mem_decs = data["memory"].get("decisions", 0)
    mem_corrs = data["memory"].get("corrections", 0)

    caps = data.get("capabilities", [])
    caps_formatted = " ".join([f"[{c}]" for c in caps[:8]])
    caps_line2 = " ".join([f"[{c}]" for c in caps[8:]]) if len(caps) > 8 else ""

    key_context = data.get("key_context", [])

    lines = [
        "═══════════════════════════════════════════════════════════════",
        "",
        f"    🐺 CERBERUS BETA    [v{version}]  [{ctx}]  [{status}]",
        "",
        "═══════════════════════════════════════════════════════════════",
        "",
        "📦 SYSTEM",
        f"   [Index: {index_age}]  [Python: {py_version}]  [Memory: {memory_total} entries]",
        "",
        "💾 MEMORY BREAKDOWN",
        f"   [{mem_prefs} preferences]  [{mem_decs} decisions]  [{mem_corrs} corrections]",
        "",
    ]

    if key_context:
        lines.append("🎯 ACTIVE CONTEXT")
        for item in key_context[:3]:
            lines.append(f"   ▸ {item}")
        lines.append("")

    lines.append("⚡ CAPABILITIES")
    lines.append(f"   {caps_formatted}")
    if caps_line2:
        lines.append(f"   {caps_line2}")
    lines.append("")
    lines.extend([
        "═══════════════════════════════════════════════════════════════",
        "Ready for optimized codebase navigation",
        "═══════════════════════════════════════════════════════════════"
    ])

    return "\n".join(lines)


def format_terminal(data: Dict[str, Any]) -> str:
    """
    Option 5: Hacker/Terminal Style (Technical)

    Args:
        data: Summary data from health_check and memory_context

    Returns:
        Formatted summary string
    """
    ctx = data["context"]
    version = data["version"]
    py_version = data.get("python_version", "unknown")
    index_path = data["index"].get("path", "N/A")
    index_age = f"{data['index'].get('age_hours', 0)}h" if data.get("index_available") else "N/A"
    memory_total = data["memory"].get("total", 0)
    mem_prefs = data["memory"].get("preferences", 0)
    mem_decs = data["memory"].get("decisions", 0)
    mem_corrs = data["memory"].get("corrections", 0)

    caps = data.get("capabilities", [])

    key_context = data.get("key_context", [])

    lines = [
        f"[INIT] Cerberus Beta v{version}",
        f"[SCAN] Context detected: {ctx}",
        f"[LOAD] Index: {index_path} (age: {index_age}) {'.' * 20} OK",
        f"[LOAD] Memory: {memory_total} entries ({mem_prefs}P/{mem_decs}D/{mem_corrs}C) {'.' * 14} OK",
        f"[LOAD] Python: {py_version} {'.' * 45} OK",
        "",
    ]

    if key_context:
        lines.append("[MEM]  Recent context:")
        for item in key_context[:3]:
            lines.append(f"       → {item}")
        lines.append("")

    lines.append("[SYS]  Capabilities online:")
    # Format caps in rows of 4
    for i in range(0, len(caps), 4):
        chunk = caps[i:i+4]
        formatted_chunk = "       " + "".join([f"[✓] {c:<12}" for c in chunk])
        lines.append(formatted_chunk)

    lines.extend([
        "",
        "[OK]   Token-optimized navigation ready",
        "[>>]   Awaiting instructions..."
    ])

    return "\n".join(lines)


# Template registry
TEMPLATES = {
    "professional": format_box,
    "minimal": format_minimal,
    "dashboard": format_dashboard,
    "modern": format_modern,  # Default
    "terminal": format_terminal,
}

# Default template name
DEFAULT_TEMPLATE = "modern"

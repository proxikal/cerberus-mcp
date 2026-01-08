"""
Agent-facing tool schemas for Cerberus.
These definitions keep contract scope small to reduce context.
"""

TOOL_SCHEMAS = {
    "GetProjectStructure": {
        "description": "Summarize project files and metadata.",
        "input_schema": {
            "type": "object",
            "properties": {
                "directory": {"type": "string", "description": "Directory to scan."},
                "respect_gitignore": {"type": "boolean", "default": True},
                "extensions": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Optional file extensions filter.",
                },
            },
            "required": ["directory"],
        },
        "output_schema": {
            "type": "object",
            "properties": {
                "total_files": {"type": "integer"},
                "files": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "path": {"type": "string"},
                            "abs_path": {"type": "string"},
                            "size": {"type": "integer"},
                            "last_modified": {"type": "number"},
                        },
                        "required": ["path", "abs_path", "size", "last_modified"],
                    },
                },
                "symbols": {"type": "array"},
                "scan_duration": {"type": "number"},
            },
            "required": ["total_files", "files", "scan_duration"],
        },
    },
    "FindSymbol": {
        "description": "Find symbols by name in an existing index.",
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "index_path": {"type": "string"},
            },
            "required": ["name", "index_path"],
        },
        "output_schema": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "symbol": {"type": "object"},
                    "snippet": {"type": "object"},
                },
                "required": ["symbol", "snippet"],
            },
        },
    },
    "ReadSymbol": {
        "description": "Read the code for a symbol with context padding.",
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "index_path": {"type": "string"},
                "padding": {"type": "integer", "default": 3},
            },
            "required": ["name", "index_path"],
        },
        "output_schema": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "symbol": {"type": "object"},
                    "snippet": {"type": "object"},
                },
                "required": ["symbol", "snippet"],
            },
        },
    },
    "SemanticSearch": {
        "description": "Search indexed symbols by meaning.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "index_path": {"type": "string"},
                "limit": {"type": "integer", "default": 5},
            },
            "required": ["query", "index_path"],
        },
        "output_schema": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "score": {"type": "number"},
                    "symbol": {"type": "object"},
                    "snippet": {"type": "object"},
                },
                "required": ["score", "symbol", "snippet"],
            },
        },
    },
}


def list_tools():
    return list(TOOL_SCHEMAS.keys())

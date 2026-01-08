import json
from pathlib import Path
from typing import Dict, Any

from cerberus.agent_tools import TOOL_SCHEMAS
from cerberus.logging_config import logger


def generate_manifest(output_path: Path = Path("tools.json")) -> Path:
    manifest = {
        "tools": [
            {
                "name": name,
                "description": schema["description"],
                "input_schema": schema["input_schema"],
                "output_schema": schema["output_schema"],
                "examples": schema.get("examples", []),
            }
            for name, schema in TOOL_SCHEMAS.items()
        ]
    }
    output_path.write_text(json.dumps(manifest, indent=2))
    logger.info(f"Wrote tool manifest to {output_path}")
    return output_path

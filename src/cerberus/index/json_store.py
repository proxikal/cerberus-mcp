import json
from pathlib import Path
from typing import Any, Dict

from cerberus.logging_config import logger
from cerberus.exceptions import IndexCorruptionError
from cerberus.schemas import (
    CallReference, CodeSymbol, FileObject, ImportReference,
    ScanResult, SymbolEmbedding, TypeInfo, ImportLink
)


class JSONIndexStore:
    """
    Minimal JSON-based storage for scan results.
    Designed as an MVP-friendly store before moving to SQLite/FAISS.
    """

    def __init__(self, path: Path):
        self.path = Path(path)

    def write(self, scan_result: ScanResult) -> Path:
        """
        Persist scan results to disk as JSON.
        """
        payload: Dict[str, Any] = {
            "files": [f.model_dump() for f in scan_result.files],
            "symbols": [s.model_dump() for s in scan_result.symbols],
            "embeddings": [e.model_dump() for e in scan_result.embeddings],
            "imports": [imp.model_dump() for imp in scan_result.imports],
            "calls": [c.model_dump() for c in scan_result.calls],
            "type_infos": [t.model_dump() for t in scan_result.type_infos],
            "import_links": [il.model_dump() for il in scan_result.import_links],
            "metadata": {
                "total_files": scan_result.total_files,
                "scan_duration": scan_result.scan_duration,
                "project_root": scan_result.project_root,
                **scan_result.metadata,  # Include custom metadata (e.g., git_commit)
            },
        }

        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(payload, indent=2))
        logger.info(f"Wrote index with {len(payload['files'])} files and {len(payload['symbols'])} symbols to {self.path}")
        return self.path

    def read(self) -> ScanResult:
        """
        Load scan results from disk and rehydrate models.

        Raises:
            IndexCorruptionError: If the index file is malformed or cannot be parsed.
        """
        try:
            if not self.path.exists():
                raise IndexCorruptionError(f"Index file not found at {self.path}")

            data = json.loads(self.path.read_text())

            # Validate basic structure
            if not isinstance(data, dict):
                raise IndexCorruptionError(f"Index file at {self.path} is not a valid JSON object")

            # Parse components with validation
            files = [FileObject(**f) for f in data.get("files", [])]
            symbols = [CodeSymbol(**s) for s in data.get("symbols", [])]
            embeddings = [SymbolEmbedding(**e) for e in data.get("embeddings", [])]
            imports = [ImportReference(**i) for i in data.get("imports", [])]
            calls = [CallReference(**c) for c in data.get("calls", [])]
            type_infos = [TypeInfo(**t) for t in data.get("type_infos", [])]
            import_links = [ImportLink(**il) for il in data.get("import_links", [])]
            meta = data.get("metadata", {})

            # Extract Phase 3 metadata
            project_root = meta.get("project_root", "")
            custom_metadata = {k: v for k, v in meta.items() if k not in ["total_files", "scan_duration", "project_root"]}

            return ScanResult(
                total_files=meta.get("total_files", len(files)),
                files=files,
                scan_duration=meta.get("scan_duration", 0.0),
                symbols=symbols,
                embeddings=embeddings,
                imports=imports,
                calls=calls,
                type_infos=type_infos,
                import_links=import_links,
                project_root=project_root,
                metadata=custom_metadata,
            )

        except json.JSONDecodeError as exc:
            raise IndexCorruptionError(f"Index file at {self.path} contains invalid JSON: {exc}")
        except (KeyError, TypeError, ValueError) as exc:
            raise IndexCorruptionError(f"Index file at {self.path} has invalid structure: {exc}")
        except Exception as exc:
            if isinstance(exc, IndexCorruptionError):
                raise
            raise IndexCorruptionError(f"Failed to read index from {self.path}: {exc}")

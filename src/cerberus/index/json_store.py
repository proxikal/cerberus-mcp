import json
from pathlib import Path
from typing import Any, Dict

from cerberus.logging_config import logger
from cerberus.schemas import CodeSymbol, FileObject, ScanResult


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
            "metadata": {
                "total_files": scan_result.total_files,
                "scan_duration": scan_result.scan_duration,
            },
        }

        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(payload, indent=2))
        logger.info(f"Wrote index with {len(payload['files'])} files and {len(payload['symbols'])} symbols to {self.path}")
        return self.path

    def read(self) -> ScanResult:
        """
        Load scan results from disk and rehydrate models.
        """
        data = json.loads(self.path.read_text())
        files = [FileObject(**f) for f in data.get("files", [])]
        symbols = [CodeSymbol(**s) for s in data.get("symbols", [])]
        embeddings = [SymbolEmbedding(**e) for e in data.get("embeddings", [])]
        meta = data.get("metadata", {})

        return ScanResult(
            total_files=meta.get("total_files", len(files)),
            files=files,
            scan_duration=meta.get("scan_duration", 0.0),
            symbols=symbols,
            embeddings=embeddings,
        )

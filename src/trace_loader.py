"""Trace loader module for reading and parsing trace files."""

import json
from pathlib import Path
from typing import Any, Dict, List


def load_traces_from_json(file_path: str) -> List[Dict[str, Any]]:
    path = Path(file_path)
    if not path.exists():
        return []
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

"""Persist posted article fingerprints to a repository-tracked JSON file."""

import json
import os
import time
from pathlib import Path

STATE_FILE = Path(__file__).resolve().parent / "state.json"
RETENTION_SECONDS = 14 * 24 * 3600


def load_history():
    """Discard old entries; reject corrupted state to avoid accidental reposting."""
    data = json.loads(STATE_FILE.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("state.json must be a JSON object")
    cutoff = time.time() - RETENTION_SECONDS
    return {
        key: timestamp
        for key, timestamp in data.items()
        if isinstance(key, str) and isinstance(timestamp, (int, float)) and timestamp >= cutoff
    }


def save_history(history):
    """Write atomically; GitHub Actions commits this file after successful delivery."""
    tmp = STATE_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(history, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, STATE_FILE)

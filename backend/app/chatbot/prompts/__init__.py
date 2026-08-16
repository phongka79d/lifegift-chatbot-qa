"""Load LLM prompts from this folder (English instructions; customer replies stay Vietnamese)."""

from pathlib import Path
from typing import Dict

_DIR = Path(__file__).resolve().parent
_NOTES = _DIR / "notes"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8").strip()


def load_prompt(name: str) -> str:
    """Load a top-level prompt file without the .txt suffix."""
    return _read(_DIR / f"{name}.txt")


def load_note(name: str) -> str:
    """Load a note template from notes/ without the .txt suffix."""
    return _read(_NOTES / f"{name}.txt")


def render_note(name: str, **kwargs: object) -> str:
    """Format a note template with keyword placeholders."""
    return load_note(name).format(**kwargs)


def load_labels() -> Dict[str, str]:
    labels: Dict[str, str] = {}
    for raw in _read(_DIR / "context_labels.txt").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        labels[key.strip()] = value.strip()
    return labels


INTENT_EXTRACTION_SYSTEM_PROMPT = load_prompt("intent_extraction_system")
ANSWER_SYSTEM_PROMPT = load_prompt("answer_system")
LABELS = load_labels()

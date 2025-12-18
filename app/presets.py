"""
Preset loader helpers.

We intentionally do not ship adult domain lists in code. Users can choose to
add `presets/adult_domains.txt` with one domain per line to start with their own
curated list. This keeps content user-supplied and avoids embedding sensitive
material.
"""

from __future__ import annotations

from pathlib import Path
from typing import List


def load_local_preset() -> List[str]:
    """Load `presets/adult_domains.txt` relative to project root if present.

    Returns a list of domains or an empty list.
    """
    try:
        project_root = Path(__file__).resolve().parent.parent
        preset_path = project_root / "presets" / "adult_domains.txt"
        if not preset_path.exists():
            return []
        raw = preset_path.read_text(encoding="utf-8", errors="ignore")
        domains = []
        for line in raw.splitlines():
            ln = line.strip()
            if not ln or ln.startswith("#"):
                continue
            domains.append(ln)
        return domains
    except Exception:
        return []

"""
State persistence for AdultBlocker.

Stores uninstall timer start timestamp and configurable domain list.
Data lives in the user's OS-specific application data directory.
- macOS: ~/Library/Application Support/<APP_NAME>
- Windows: %APPDATA%\\<APP_NAME>
No user activity is tracked; only configuration and timer state are stored.
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Dict, List, Optional
import platform

DEFAULT_DOMAINS = [
    # Minimal default; replace or expand via UI. Examples only.
    "exampleadult.com",
    "www.exampleadult.com",
]


class StateStore:
    """Simple JSON-backed state store with defensive IO.

    Schema (subject to change as app evolves):
    {
        "blocked_domains": List[str],
        "pending_uninstall_started_at": Optional[float],  # seconds since epoch
        "onboarding_completed": bool,
    }
    """

    def __init__(self, app_name: str):
        self.app_name = app_name
        self.app_dir = self._resolve_app_data_dir(app_name)
        self.state_path = self.app_dir / "state.json"
        self.app_dir.mkdir(parents=True, exist_ok=True)
        if not self.state_path.exists():
            # Try to load a starter preset (user-supplied) if present.
            starter = self._load_preset_domains_if_available()
            self._write_state({
                "blocked_domains": starter if starter else DEFAULT_DOMAINS,
                "pending_uninstall_started_at": None,
                "onboarding_completed": False,
            })

    @staticmethod
    def _resolve_app_data_dir(app_name: str) -> Path:
        system = platform.system().lower()
        if system == "darwin":  # macOS
            return Path.home() / "Library" / "Application Support" / app_name
        elif system == "windows":
            base = os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming")
            return Path(base) / app_name
        else:  # linux/other
            return Path.home() / f".{app_name.lower()}"

    def _write_state(self, data: Dict) -> None:
        tmp = self.state_path.with_suffix(".tmp")
        tmp.write_text(json.dumps(data, indent=2))
        tmp.replace(self.state_path)

    def _load_preset_domains_if_available(self) -> Optional[List[str]]:
        """Load starter domains from presets/adult_domains.txt if present.

        We do not ship any domain list; users can add their own file.
        Lines are treated as domains; blank/comment lines are ignored.
        """
        try:
            # Look for a presets file relative to the project/app package.
            project_root = Path(__file__).resolve().parent.parent
            preset_path = project_root / "presets" / "adult_domains.txt"
            if not preset_path.exists():
                return None
            raw = preset_path.read_text(encoding="utf-8", errors="ignore")
            domains: List[str] = []
            for line in raw.splitlines():
                ln = line.strip()
                if not ln or ln.startswith("#"):
                    continue
                domains.append(ln)
            return domains or None
        except Exception:
            return None

    def load(self) -> Dict:
        try:
            raw = self.state_path.read_text()
            data = json.loads(raw)
            # fill defaults if missing
            data.setdefault("blocked_domains", DEFAULT_DOMAINS)
            data.setdefault("pending_uninstall_started_at", None)
            data.setdefault("onboarding_completed", False)
            return data
        except Exception:
            # If corrupt, reset to defaults (transparent, no hidden behavior)
            reset = {
                "blocked_domains": DEFAULT_DOMAINS,
                "pending_uninstall_started_at": None,
                "onboarding_completed": False,
            }
            self._write_state(reset)
            return reset

    def save(self, data: Dict) -> None:
        self._write_state(data)

    # Convenience helpers
    def get_domains(self) -> List[str]:
        return list(self.load().get("blocked_domains", DEFAULT_DOMAINS))

    def set_domains(self, domains: List[str]) -> None:
        state = self.load()
        state["blocked_domains"] = [d.strip() for d in domains if d.strip()]
        self.save(state)

    def start_uninstall_timer(self) -> None:
        state = self.load()
        state["pending_uninstall_started_at"] = time.time()
        self.save(state)

    def cancel_uninstall_timer(self) -> None:
        state = self.load()
        state["pending_uninstall_started_at"] = None
        self.save(state)

    def get_uninstall_started_at(self) -> Optional[float]:
        val = self.load().get("pending_uninstall_started_at")
        if isinstance(val, (int, float)):
            return float(val)
        return None

    def uninstall_ready(self, delay_seconds: int) -> bool:
        started = self.get_uninstall_started_at()
        if started is None:
            return False
        return (time.time() - started) >= delay_seconds

    # Onboarding helpers
    def is_onboarding_completed(self) -> bool:
        return bool(self.load().get("onboarding_completed", False))

    def set_onboarding_completed(self, completed: bool = True) -> None:
        state = self.load()
        state["onboarding_completed"] = bool(completed)
        self.save(state)

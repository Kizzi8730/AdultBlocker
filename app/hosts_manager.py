"""
System hosts file manager for AdultBlocker.

Edits the OS hosts file to redirect configured domains to 127.0.0.1.
- Idempotent: uses start/end markers to manage its own block section.
- Transparent: communicates permissions; does not obfuscate or hide changes.
- Reversible: removal restores the previous state (outside our section).

Note: Modifying the hosts file requires administrator/root privileges.
This module will raise exceptions if permission is denied; UI should surface
clear instructions on how to run with elevated privileges only when needed.
"""

from __future__ import annotations

import platform
from pathlib import Path
from typing import List
import subprocess

BLOCK_START = "# AdultBlocker START"
BLOCK_END = "# AdultBlocker END"


class HostsManager:
    def __init__(self, app_name: str):
        self.app_name = app_name
        self.hosts_path = self._resolve_hosts_path()

    @staticmethod
    def _resolve_hosts_path() -> Path:
        system = platform.system().lower()
        if system == "windows":
            return Path(r"C:\\Windows\\System32\\drivers\\etc\\hosts")
        else:  # macOS/Linux
            return Path("/etc/hosts")

    def _read_hosts(self) -> str:
        return self.hosts_path.read_text(encoding="utf-8", errors="ignore")

    def _write_hosts(self, content: str) -> None:
        self.hosts_path.write_text(content, encoding="utf-8")

    def _expand_domains(self, domains: List[str]) -> List[str]:
        expanded = set()
        for d in domains:
            d = d.strip()
            if not d:
                continue
            expanded.add(d)
            if not d.startswith("www."):
                expanded.add("www." + d)
        return sorted(expanded)

    def is_block_active(self, domains: List[str]) -> bool:
        content = self._read_hosts()
        if BLOCK_START not in content or BLOCK_END not in content:
            return False
        block_section = content.split(BLOCK_START, 1)[1].split(BLOCK_END, 1)[0]
        expanded = self._expand_domains(domains)
        return all(any(line.strip().endswith(f" {d}") for line in block_section.splitlines()) for d in expanded)

    def apply_block(self, domains: List[str]) -> None:
        expanded = self._expand_domains(domains)
        content = self._read_hosts()

        # Remove any existing block section first (idempotency)
        if BLOCK_START in content and BLOCK_END in content:
            before, rest = content.split(BLOCK_START, 1)
            _, after = rest.split(BLOCK_END, 1)
            content = before + after

        lines = [
            BLOCK_START,
            "# The following entries were added by AdultBlocker to intentionally block domains.",
            "# Remove this section to unblock (requires admin/root).",
        ]
        for d in expanded:
            lines.append(f"127.0.0.1 {d}")
            lines.append(f"::1 {d}")
        lines.append(BLOCK_END)
        block = "\n".join(lines) + "\n"

        if content and not content.endswith("\n"):
            content += "\n"
        new_content = content + block
        self._write_hosts(new_content)
        self.flush_dns()

    def remove_block(self) -> None:
        content = self._read_hosts()
        if BLOCK_START in content and BLOCK_END in content:
            before, rest = content.split(BLOCK_START, 1)
            _, after = rest.split(BLOCK_END, 1)
            self._write_hosts(before + after)
            self.flush_dns()
        # If no block markers, nothing to do.

    def flush_dns(self) -> None:
        """Best-effort DNS cache flush to make hosts changes take effect sooner.

        - macOS: dscacheutil + mDNSResponder
        - Windows: ipconfig /flushdns
        - Linux: try resolvectl or nscd if available (ignored if not).
        """
        system = platform.system().lower()
        try:
            if system == "darwin":
                subprocess.run(["/usr/bin/dscacheutil", "-flushcache"], check=False)
                subprocess.run(["/usr/bin/killall", "-HUP", "mDNSResponder"], check=False)
            elif system == "windows":
                subprocess.run(["ipconfig", "/flushdns"], check=False)
            else:
                # Linux / others
                subprocess.run(["resolvectl", "flush-caches"], check=False)
                subprocess.run(["systemd-resolve", "--flush-caches"], check=False)
                subprocess.run(["nscd", "-i", "hosts"], check=False)
        except Exception:
            # Ignore errors silently; flushing is best-effort.
            pass

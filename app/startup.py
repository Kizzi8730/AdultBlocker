"""
Startup checks and self-healing logic.

- Ensures configured domains are blocked at app launch.
- If the block section was removed externally, re-applies it.
- Leaves uninstall timer state untouched (respect user agency).
"""

from __future__ import annotations

from app.state_store import StateStore
from app.hosts_manager import HostsManager


class Startup:
    @staticmethod
    def ensure_consistency(state: StateStore, hosts: HostsManager) -> None:
        domains = state.get_domains()
        try:
            if not hosts.is_block_active(domains):
                hosts.apply_block(domains)
                # Best-effort cache flush already handled inside apply_block
        except PermissionError:
            # Not enough privileges to re-apply; UI will inform the user.
            # We avoid hidden behavior or retries here.
            pass
        except Exception:
            # Defensive: do not crash UI on startup if hosts edit fails.
            pass

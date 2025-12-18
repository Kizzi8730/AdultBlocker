"""
Minimal PyQt6 UI for AdultBlocker.

Provides:
- Status display: Active, Pending uninstall with countdown, or Ready to uninstall.
- Buttons: Start Uninstall (15-min delay), Cancel Uninstall, Proceed Uninstall.
- Domain editing: simple dialog to edit newline-separated list.

Blocking remains active during the uninstall timer; only after the timer
completes can the user proceed to uninstall (remove the block section).
"""

from __future__ import annotations

import time
from typing import List

from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QLabel,
    QPushButton,
    QHBoxLayout,
    QDialog,
    QTextEdit,
    QDialogButtonBox,
    QMessageBox,
    QGroupBox,
)

from app.state_store import StateStore
from app.hosts_manager import HostsManager

UNINSTALL_DELAY_SECONDS = 15 * 60


class EditDomainsDialog(QDialog):
    def __init__(self, domains: List[str], parent: QWidget | None = None):
        super().__init__(parent)
        self.setWindowTitle("Edit Blocked Domains")
        layout = QVBoxLayout(self)

        self.editor = QTextEdit(self)
        self.editor.setPlainText("\n".join(domains))
        layout.addWidget(self.editor)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel,
            parent=self,
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def get_domains(self) -> List[str]:
        return [line.strip() for line in self.editor.toPlainText().splitlines() if line.strip()]


class AdultBlockerWindow(QWidget):
    def __init__(self, state: StateStore, hosts: HostsManager):
        super().__init__()
        self.state = state
        self.hosts = hosts

        self.setWindowTitle("AdultBlocker — you're in control")
        self.resize(560, 280)

        self.status_label = QLabel("", self)
        self.status_label.setStyleSheet("font-size:16px; font-weight:600; color:#1a1a1a;")

        self.start_uninstall_btn = QPushButton("Start 15-min turn-off timer", self)
        self.cancel_uninstall_btn = QPushButton("Keep blocking (cancel)", self)
        self.proceed_uninstall_btn = QPushButton("Turn off blocking", self)
        self.edit_domains_btn = QPushButton("Edit domains…", self)
        self.apply_block_btn = QPushButton("Apply / re-apply blocks", self)
        self.uninstall_app_btn = QPushButton("Uninstall App", self)

        btn_row1 = QHBoxLayout()
        btn_row1.addWidget(self.start_uninstall_btn)
        btn_row1.addWidget(self.cancel_uninstall_btn)

        btn_row2 = QHBoxLayout()
        btn_row2.addWidget(self.proceed_uninstall_btn)
        btn_row2.addWidget(self.edit_domains_btn)
        btn_row2.addWidget(self.apply_block_btn)

        btn_row3 = QHBoxLayout()
        btn_row3.addWidget(self.uninstall_app_btn)

        layout = QVBoxLayout(self)
        status_box = QGroupBox("Status")
        status_layout = QVBoxLayout(status_box)
        status_layout.addWidget(self.status_label)
        layout.addWidget(status_box)

        actions_box = QGroupBox("Actions")
        actions_layout = QVBoxLayout(actions_box)
        actions_layout.addLayout(btn_row1)
        actions_layout.addLayout(btn_row2)
        actions_layout.addLayout(btn_row3)
        layout.addWidget(actions_box)

        # Simple, friendly tone for tooltips
        self.start_uninstall_btn.setToolTip("Start a short timer before making changes")
        self.cancel_uninstall_btn.setToolTip("Keep things as they are")
        self.proceed_uninstall_btn.setToolTip("Turn blocking off after the timer")
        self.apply_block_btn.setToolTip("Turn blocking on or refresh it")
        self.edit_domains_btn.setToolTip("Edit your list after the timer")
        self.uninstall_app_btn.setToolTip("Remove all blocks and uninstall the app")

        self.timer = QTimer(self)
        self.timer.setInterval(1000)
        self.timer.timeout.connect(self._update_status)
        self.timer.start()

        self.start_uninstall_btn.clicked.connect(self._start_uninstall)
        self.cancel_uninstall_btn.clicked.connect(self._cancel_uninstall)
        self.proceed_uninstall_btn.clicked.connect(self._proceed_uninstall)
        self.edit_domains_btn.clicked.connect(self._edit_domains)
        self.apply_block_btn.clicked.connect(self._apply_blocks)
        self.uninstall_app_btn.clicked.connect(self._uninstall_app)

        self._update_status()

    def _uninstall_app(self) -> None:
        # Require timer to be ready
        if not self._require_timer_ready("uninstall the app"):
            return
        reply = QMessageBox.question(
            self,
            "Uninstall App",
            "This will remove all website blocks and prepare the app for deletion. Continue?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        try:
            self.hosts.remove_block()
            self.state.cancel_uninstall_timer()
            QMessageBox.information(
                self,
                "Uninstalled",
                "App uninstalled. All website blocks removed.\nYou can now delete this app from your computer."
            )
            self.close()
        except PermissionError:
            QMessageBox.warning(self, "Permission needed", (
                "Editing the hosts file needs administrator/root access.\nRun this app with elevated permissions to uninstall."
            ))
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to uninstall: {e}")

    def _start_uninstall(self) -> None:
        self.state.start_uninstall_timer()
        self._update_status()

    def _cancel_uninstall(self) -> None:
        self.state.cancel_uninstall_timer()
        self._update_status()

    def _proceed_uninstall(self) -> None:
        # Only allowed if timer completed
        if not self.state.uninstall_ready(UNINSTALL_DELAY_SECONDS):
            QMessageBox.information(self, "Not Ready", "Uninstall becomes available once the 15-minute timer completes.")
            return
        try:
            self.hosts.remove_block()
            self.state.cancel_uninstall_timer()
            QMessageBox.information(self, "Blocking turned off", "Entries removed from the hosts file. You can turn blocking back on anytime.")
        except PermissionError:
            QMessageBox.warning(self, "Permission needed", (
                "Editing the hosts file needs administrator/root access.\n"
                "Run this app with elevated permissions to turn blocking off."
            ))
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to modify hosts file: {e}")
        finally:
            self._update_status()

    def _edit_domains(self) -> None:
        # Editing domains requires the turn-off timer to be completed.
        if not self._require_timer_ready("edit your domain list"):
            return
        dialog = EditDomainsDialog(self.state.get_domains(), self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.state.set_domains(dialog.get_domains())
            QMessageBox.information(self, "Saved", "Domains updated. Re-applying keeps things tidy.")
            self._update_status()

    def _apply_blocks(self) -> None:
        domains = self.state.get_domains()
        try:
            self.hosts.apply_block(domains)
            QMessageBox.information(self, "Blocking on", "Domains are now routed to your device (hosts file). We also refreshed the DNS cache.")
        except PermissionError:
            QMessageBox.warning(self, "Permission needed", (
                "Editing the hosts file needs administrator/root access.\n"
                "Run this app with elevated permissions to apply blocks."
            ))
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to modify hosts file: {e}")
        finally:
            self._update_status()

    def _update_status(self) -> None:
        started = self.state.get_uninstall_started_at()
        now = time.time()
        if started is None:
            # Active state (blocking expected to be active)
            self.start_uninstall_btn.setEnabled(True)
            self.cancel_uninstall_btn.setEnabled(False)
            self.proceed_uninstall_btn.setEnabled(False)
            self.status_label.setText("Blocking is ON")
            self.edit_domains_btn.setEnabled(False)
            self.uninstall_app_btn.setEnabled(False)
        else:
            remaining = int(max(0, UNINSTALL_DELAY_SECONDS - (now - started)))
            if remaining > 0:
                mins = remaining // 60
                secs = remaining % 60
                self.status_label.setText(f"Turn-off timer running — {mins:02d}:{secs:02d} left")
                self.start_uninstall_btn.setEnabled(False)
                self.cancel_uninstall_btn.setEnabled(True)
                self.proceed_uninstall_btn.setEnabled(False)
                # Editing and uninstall are disabled until timer completes
                self.edit_domains_btn.setEnabled(False)
                self.uninstall_app_btn.setEnabled(False)
            else:
                self.status_label.setText("Timer done — you can turn blocking off")
                self.start_uninstall_btn.setEnabled(False)
                self.cancel_uninstall_btn.setEnabled(True)
                self.proceed_uninstall_btn.setEnabled(True)
                # After timer, allow domain edits and uninstall
                self.edit_domains_btn.setEnabled(True)
                self.uninstall_app_btn.setEnabled(True)

    # Public helpers for tray actions (friendly names)
    def start_timer(self) -> None:
        self._start_uninstall()

    def cancel_timer(self) -> None:
        self._cancel_uninstall()

    def turn_off_blocking(self) -> None:
        self._proceed_uninstall()

    def apply_blocks(self) -> None:
        self._apply_blocks()


    def _require_timer_ready(self, purpose: str) -> bool:
        """Return True if uninstall timer completed; otherwise guide the user.

        We reuse the same 15-minute timer for intentional changes like editing
        or importing domain lists to maintain friction and user intent.
        """
        if self.state.uninstall_ready(UNINSTALL_DELAY_SECONDS):
            return True
        started = self.state.get_uninstall_started_at()
        if started is None:
            resp = QMessageBox.question(
                self,
                "Timer needed",
                (
                    f"To {purpose}, please start a short 15-minute timer.\n"
                    "Blocking stays ON during the timer. Start now?"
                ),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if resp == QMessageBox.StandardButton.Yes:
                self.state.start_uninstall_timer()
                self._update_status()
            return False
        # Timer running but not done yet
        remaining = int(max(0, UNINSTALL_DELAY_SECONDS - (time.time() - started)))
        mins = remaining // 60
        secs = remaining % 60
        QMessageBox.information(self, "Timer running", f"Please wait {mins:02d}:{secs:02d} before continuing.")
        return False

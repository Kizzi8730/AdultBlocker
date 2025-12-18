"""
Onboarding dialog shown on first run.

- Simple language: explains what the app does and permission needs.
- Lets the user pick domains from a user-supplied preset file or import one.
- Installs (applies blocks) and marks onboarding complete.

We intentionally avoid shipping adult domain names in code. The dialog loads
`presets/adult_domains.txt` if present, or allows importing a text file.
"""

from __future__ import annotations

from typing import List
from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QHBoxLayout,
    QPushButton,
    QMessageBox,
    QLineEdit,
)

from app.state_store import StateStore
from app.hosts_manager import HostsManager


class OnboardingDialog(QDialog):
    def __init__(self, state: StateStore, hosts: HostsManager, parent=None):
        super().__init__(parent)
        self.state = state
        self.hosts = hosts
        self.setWindowTitle("Welcome — set things up")
        self.resize(600, 420)
        self.setModal(True)
        layout = QVBoxLayout(self)

        intro = QLabel(
            "AdultBlocker helps you block websites you choose.\n"
            "You’re always in control. Turning things off has a short,\n"
            "intentional 15-minute delay.\n\n"
            "Note: To install blocks, we need admin permission to edit the hosts file.")
        intro.setWordWrap(True)
        layout.addWidget(intro)

        self.list = QListWidget(self)
        self.list.setSelectionMode(QListWidget.SelectionMode.NoSelection)
        layout.addWidget(QLabel("Pick the websites you want to block:"))

        # Add domain input row
        add_row = QHBoxLayout()
        self.new_domain_input = QLineEdit(self)
        self.new_domain_input.setPlaceholderText("example.com")
        self.add_domain_btn = QPushButton("Add", self)
        add_row.addWidget(self.new_domain_input)
        add_row.addWidget(self.add_domain_btn)
        layout.addLayout(add_row)

        layout.addWidget(self.list)

        btn_row = QHBoxLayout()
        self.select_all_btn = QPushButton("Select all", self)
        self.clear_all_btn = QPushButton("Clear all", self)
        self.install_btn = QPushButton("Install blocking", self)
        # No file import; show controls for selection
        btn_row.addWidget(self.select_all_btn)
        btn_row.addWidget(self.clear_all_btn)
        btn_row.addWidget(self.install_btn)
        layout.addLayout(btn_row)

        self.select_all_btn.clicked.connect(self._select_all)
        self.clear_all_btn.clicked.connect(self._clear_all)
        self.install_btn.clicked.connect(self._install)
        self.add_domain_btn.clicked.connect(self._add_domain)

        self._load_preset()

    def _load_preset(self) -> None:
        try:
            project_root = Path(__file__).resolve().parent.parent
            preset_path = project_root / "presets" / "adult_domains.txt"
            if preset_path.exists():
                raw = preset_path.read_text(encoding="utf-8", errors="ignore")
                domains = [ln.strip() for ln in raw.splitlines() if ln.strip() and not ln.strip().startswith('#')]
                self._populate(domains)
            else:
                self._populate([])
        except Exception:
            self._populate([])

    def _populate(self, domains: List[str]) -> None:
        self.list.clear()
        if not domains:
            item = QListWidgetItem("No starter list found. Import your list to begin.")
            item.setFlags(Qt.ItemFlag.NoItemFlags)
            self.list.addItem(item)
            return
        for d in domains:
            item = QListWidgetItem(d)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Checked)
            self.list.addItem(item)

    def _add_domain(self) -> None:
        text = (self.new_domain_input.text() or "").strip().lower()
        if not text:
            QMessageBox.information(self, "Add a website", "Type a website like example.com.")
            return
        # Simple validation: letters, numbers, hyphens and dots; must contain a dot.
        allowed = set("abcdefghijklmnopqrstuvwxyz0123456789-.")
        if any(ch not in allowed for ch in text) or "." not in text or text.startswith(".") or text.endswith("."):
            QMessageBox.information(self, "Not a website", "Please enter a website like example.com.")
            return
        # Prevent duplicates
        for i in range(self.list.count()):
            it = self.list.item(i)
            if it and it.text().strip().lower() == text:
                QMessageBox.information(self, "Already added", "That website is already in the list.")
                return
        item = QListWidgetItem(text)
        item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
        item.setCheckState(Qt.CheckState.Checked)
        self.list.addItem(item)
        self.new_domain_input.clear()

    def _select_all(self) -> None:
        for i in range(self.list.count()):
            item = self.list.item(i)
            if item is None:
                continue
            if item.flags() & Qt.ItemFlag.ItemIsUserCheckable:
                item.setCheckState(Qt.CheckState.Checked)

    def _clear_all(self) -> None:
        for i in range(self.list.count()):
            item = self.list.item(i)
            if item is None:
                continue
            if item.flags() & Qt.ItemFlag.ItemIsUserCheckable:
                item.setCheckState(Qt.CheckState.Unchecked)

    # File import removed per request; onboarding uses local preset or empty list.

    def _selected_domains(self) -> List[str]:
        out: List[str] = []
        for i in range(self.list.count()):
            item = self.list.item(i)
            # Guard for Optional[QListWidgetItem] to satisfy type checkers
            if item is None:
                continue
            flags = item.flags()
            if (flags & Qt.ItemFlag.ItemIsUserCheckable) and item.checkState() == Qt.CheckState.Checked:
                out.append(item.text().strip())
        return out

    def _install(self) -> None:
        domains = self._selected_domains()
        if not domains:
            QMessageBox.information(self, "Pick some first", "Please choose at least one website to block.")
            return
        try:
            self.state.set_domains(domains)
            self.hosts.apply_block(domains)
            self.state.set_onboarding_completed(True)
            QMessageBox.information(self, "Done", "Blocking is set up. You’ll find the app in the tray; open it anytime.")
            self.accept()
        except PermissionError:
            QMessageBox.warning(self, "Permission needed", (
                "We need admin/root permission to install blocking.\n"
                "Please re-run the app with elevated permissions and try again."
            ))
            # Mark onboarding as complete so the app can proceed; user can apply later.
            self.state.set_onboarding_completed(True)
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not install blocking: {e}")

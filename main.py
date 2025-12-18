"""
AdultBlocker - Minimal, ethical desktop app to help users block adult websites.

Entry point: boots the PyQt6 UI, wires core modules, and keeps logic minimal.

Design principles:
- Voluntary: user initiates blocking and uninstall.
- Respectful: no shame, no surveillance, no data collection.
- Transparent: requires admin/root to modify hosts; communicates clearly.
- Reversible: uninstall is possible after a 15-minute intentional delay.

Packaging: later with PyInstaller.
"""

from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QIcon, QPixmap
from PyQt6.QtWidgets import QSystemTrayIcon, QMenu
from PyQt6.QtGui import QAction
from PyQt6.QtGui import QPainter, QColor, QFont
import sys

from app.ui import AdultBlockerWindow
from app.state_store import StateStore
from app.hosts_manager import HostsManager
from app.startup import Startup
from app.onboarding import OnboardingDialog

APP_NAME = "AdultBlocker"


import traceback
from PyQt6.QtWidgets import QMessageBox

def main() -> None:
    def excepthook(type_, value, tb):
        msg = ''.join(traceback.format_exception(type_, value, tb))
        print(msg)
        try:
            QMessageBox.critical(None, "Unexpected Error", msg)
        except Exception:
            pass
    import sys
    sys.excepthook = excepthook
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setOrganizationName("AdultBlocker")
    # Let the OS choose the native style and palette for best readability.
    state = StateStore(APP_NAME)
    hosts = HostsManager(APP_NAME)

    Startup.ensure_consistency(state, hosts)

    # Onboarding on first run
    if not state.is_onboarding_completed():
        ob = OnboardingDialog(state, hosts)
        ob.exec()

    window = AdultBlockerWindow(state, hosts)

    # Create a simple tray icon so the app can stay in the background.
    # We generate a minimal in-memory icon.
    pix = QPixmap(64, 64)
    pix.fill(QColor(245, 245, 247))
    p = QPainter(pix)
    p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    # Simple badge
    p.setBrush(QColor(50, 120, 220))
    p.setPen(QColor(50, 120, 220))
    p.drawRoundedRect(4, 4, 56, 56, 10, 10)
    p.setPen(QColor(255, 255, 255))
    f = QFont()
    f.setBold(True)
    f.setPointSize(20)
    p.setFont(f)
    p.drawText(pix.rect(), 0x84, "AB")  # center
    p.end()
    icon = QIcon(pix)
    tray = None
    if QSystemTrayIcon.isSystemTrayAvailable():
        tray = QSystemTrayIcon(icon)
        tray.setToolTip(APP_NAME)
        menu = QMenu()
        action_open = QAction("Open AdultBlocker", menu)
        menu.addAction(action_open)
        action_start_timer = QAction("Start 15-min timer", menu)
        menu.addAction(action_start_timer)
        action_cancel_timer = QAction("Cancel timer", menu)
        menu.addAction(action_cancel_timer)
        action_turn_off = QAction("Turn off blocking", menu)
        menu.addAction(action_turn_off)
        action_apply = QAction("Apply blocks", menu)
        menu.addAction(action_apply)
        menu.addSeparator()
        action_quit = QAction("Quit", menu)
        menu.addAction(action_quit)

    def _open():
        window.show()
        window.raise_()
        window.activateWindow()

    def _quit():
        app.quit()

    def _start_timer():
        window.start_timer()

    def _cancel_timer():
        window.cancel_timer()

    def _turn_off():
        window.turn_off_blocking()

    def _apply():
        window.apply_blocks()

    if tray is not None:
        action_open.triggered.connect(_open)
        action_start_timer.triggered.connect(_start_timer)
        action_cancel_timer.triggered.connect(_cancel_timer)
        action_turn_off.triggered.connect(_turn_off)
        action_apply.triggered.connect(_apply)
        action_quit.triggered.connect(_quit)
        tray.setContextMenu(menu)
        tray.show()

    # Always show the window on launch to ensure visibility.
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()

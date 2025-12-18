
# AdultBlocker (Minimal Starter)

A small, ethical desktop app (Python + PyQt6) that helps users block adult websites by adding intentional friction to uninstall while fully respecting user agency.

## Principles
- Voluntary: blocking starts and ends by user choice.
- Respectful: no shame, no surveillance, no data collection.
- Transparent: uses system hosts file with clear markers, requires admin/root.
- Reversible: uninstall available after a 15-minute delay; no lockouts.

## Tech Stack
- Python 3.10+
- PyQt6 for GUI
- Packaging later with PyInstaller

## How It Works
- Blocks domains by adding entries between `# AdultBlocker START` and `# AdultBlocker END` in the system hosts file.
- Re-applies blocks on startup if they were removed.
- Turn-off flow uses a 15-minute timer; blocking stays active during the timer. When the timer completes, you can turn blocking off (remove the block section).

## Permissions
Editing the hosts file requires administrator/root privileges:
- macOS/Linux: run via `sudo` or launch with elevated privileges.
- Windows: run from an elevated (Administrator) prompt.
The UI will show clear messages when permissions are missing; no hidden behavior.

## Project Structure
```
.
├── main.py                # Entry point
├── app/
│   ├── __init__.py
│   ├── ui.py              # PyQt6 UI and timer logic
│   ├── hosts_manager.py   # Hosts file application/removal/check
│   ├── state_store.py     # JSON persistence for domains + uninstall timer
│   └── startup.py         # Startup self-healing for block re-application
├── presets/
│   └── adult_domains.txt  # Optional user-supplied starter list (not shipped)
├── README.md
└── requirements.txt
```

## Quick Start
1. Create a virtual environment and install dependencies:

```zsh
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

2. Run the app using the venv Python (non-elevated is fine to explore; hosts edits will require elevation). Avoid the system Apple Python:

```zsh
./scripts/run.sh
```

3. To apply or remove blocks, run elevated:

```zsh
sudo -E python3 main.py
```

On Windows, run from an Administrator PowerShell:
```
py -3 main.py
```

## Design Notes
- Idempotent hosts edits: we always remove our section then re-add it to avoid duplication.
- Minimal defaults: example domains only; you can edit in the UI.
- No tracking: we store only the domain list and uninstall timer start time.
- Self-healing: if someone removes our section externally, we reapply on startup (assuming permissions).
 - Presets: if you add `presets/adult_domains.txt`, the app will use it on first run. Editing the list is available in the UI after the timer.
 - Intent for edits: editing or importing domain lists uses the same 15-minute timer as turning blocking off (adds friction; blocking stays ON during the timer).
 - IPv4+IPv6: we add both `127.0.0.1` and `::1` entries for better coverage.
 - DNS cache: we try to refresh OS DNS caches after changes so blocks take effect quickly.

## Troubleshooting on macOS
If you see an error like `Could not find the Qt platform plugin "cocoa"`:
- Make sure you’re running with the venv Python (`./scripts/run.sh`) rather than the system Apple Python.
- If needed, reinstall PyQt6 in the venv:

```zsh
source .venv/bin/activate
pip uninstall -y PyQt6 PyQt6-Qt6 PyQt6-sip
pip install --upgrade pip
pip install PyQt6
```

If the app launches but no window shows, it’s likely sitting in the tray. Click the tray icon and choose “Open AdultBlocker”.

## Download & Run from GitHub
1. Clone the repo:

```zsh
git clone https://github.com/<you>/adultblocker.git
cd adultblocker
```

2. Run with the helper (uses a venv):

```zsh
./scripts/run.sh
```

3. Install blocking (requires admin/root): open the UI or use tray — it will guide you. If you need elevation:

```zsh
 sudo -E ./scripts/run.sh
 # After changes, if needed, you can manually flush DNS:
 # macOS:  dscacheutil -flushcache; killall -HUP mDNSResponder
 # Windows: ipconfig /flushdns
```

## Packaging for Others
- macOS:

```zsh
./scripts/build-macos.sh
open dist/AdultBlocker.app
```

- Windows (PowerShell as Administrator recommended for install/apply):

```powershell
./scripts/build-windows.ps1
start dist/AdultBlocker/AdultBlocker.exe
```

Optional but recommended for distribution:
- Code signing (Windows) and notarization (macOS) to avoid warning prompts.
- Ship a signed installer (.dmg/.pkg for macOS, .msi/.exe for Windows).

## Start at Login (optional)
- macOS: create a LaunchAgent plist to run the app on login (documented templates can be added later).
- Windows: add a Task Scheduler task or Startup entry to run the app at user logon.

## UI Notes
- Friendly, plain language; minimal tech jargon.
- Changes like editing domains or turning blocking off use a short 15‑minute timer; blocking stays ON during the timer.
- Tray icon provides quick actions: open app, start/cancel timer, turn off blocking, apply blocks.

## Packaging (later)
- PyInstaller can produce platform-specific binaries:
  - macOS: `pyinstaller --windowed --name AdultBlocker main.py`
  - Windows: `pyinstaller --noconsole --name AdultBlocker main.py`

## Ethics
This project is designed to help you follow through on your own choices. No shaming, no tracking, and you’re always in control. Turning off blocking has a short, intentional delay but it’s always available.

# AdultBlocker
Blocks adult websites


# PhonePad

Use your phone's touchscreen as a touchpad (and basic keyboard) for your PC.

A native **Android app** captures gestures and a small **Python server** on the PC
turns them into real mouse/keyboard actions via
[pynput](https://pypi.org/project/pynput/). Both devices must be on the **same
Wi-Fi / LAN**.

> Note: this implements the core touchpad over a native Android app + raw TCP
> socket (not the earlier Flask/WebSocket/HTML idea). Media keys, volume and
> clipboard sync are easy follow-ups — see "Protocol" below.

## PC server

A small, dark, low-RAM tray app (Tkinter + pystray, ~40 MB). Requirements:
Python 3.8+ on the PC.

First-time setup — install dependencies:

```bash
pip install -r requirements.txt
```

Then launch it any of these ways:

- The **PhonePad Server** shortcut on your Desktop or in the Start Menu
  (created by `make_shortcuts.ps1`, uses `phonepad.ico`).
- Double-click **`run.bat`** (installs deps if needed, then starts the app).
- `pythonw server.py` from a terminal.

All launch with `pythonw` (no console window). The window shows the PC's IP and
port and how many phones are connected.

- **Closing the window with the X** hides it to the system tray — the server
  keeps running. Click the tray icon (or its "Show PhonePad" menu) to reopen.
- **Quit** (button in the window, or the tray menu) closes it completely.

To launch PhonePad automatically at login, run
`powershell -ExecutionPolicy Bypass -File make_shortcuts.ps1 -AutoStart`. To
turn it off again, delete `PhonePad Server.lnk` from your Startup folder
(`shell:startup`).

The server listens on:

- **TCP 5000** – the command stream from the phone
- **UDP 5001** – auto-discovery, so the phone can find the PC without typing an IP

If the phone can't connect, allow `python.exe` / `pythonw.exe` through the
Windows Firewall on private networks (Windows usually prompts the first time).

## Phone app

The Android project lives in `../AndroidProjects/PhonePad`. Open it in Android
Studio and Run, or install the prebuilt debug APK:

```
adb install -r app/build/outputs/apk/debug/app-debug.apk
```

In the app:

1. Tap **Search for PC on this Wi-Fi** and pick your PC, or type its IP manually
   (port `5000`).
2. Use the touchpad surface:

| Gesture | Action |
| --- | --- |
| One finger drag | Move cursor |
| One finger tap | Left click |
| Two finger tap | Right click |
| Two finger drag | Scroll |
| Double-tap then hold + drag | Click-and-drag |

There are also on-screen **Left / Middle / Right** click buttons and a
**Show keyboard** panel for typing to the PC.

Tap **⚙ Settings** on the start screen (before connecting) to adjust:

- **Reverse scroll** – drag down → scroll up (on) vs. natural (off)
- **Pointer speed** and **Scroll speed** multipliers

## Protocol

The phone streams newline-delimited text commands over TCP. Adding new buttons
(media keys, volume, clipboard) is mostly a matter of adding cases here and in
`server.py`:

```
M <dx> <dy>   relative mouse move      S <dx> <dy>  scroll
LC RC MC DC   left/right/middle/double click
LD / LU       left button down / up (drag)
K <text>      type text                SK <name>    special key (enter, backspace, ...)
```

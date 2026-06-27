"""PhonePad PC server — lightweight tray app.

Turns your phone into a touchpad for this PC. The phone connects over TCP and
streams compact one-line commands that we translate into mouse/keyboard actions
with pynput. A small UDP responder lets the phone discover this PC automatically.

This is a small Tkinter window (dark, minimal) that lives in the system tray:
  * Closing the window with the X hides it to the tray (server keeps running).
  * Use the tray menu, or the "Quit" button in the window, to exit completely.

Run:  pythonw server.py     (or double-click run.bat / the desktop shortcut)
"""

import socket
import threading
import time

from pynput.mouse import Button, Controller as MouseController
from pynput.keyboard import Key, Controller as KeyboardController

# ---- Configuration ---------------------------------------------------------

TCP_PORT = 5000          # phone connects here and streams commands
DISCOVERY_PORT = 5001    # phone broadcasts here to find this PC
DISCOVERY_MAGIC = b"PHONEPAD_DISCOVER"
DISCOVERY_REPLY_PREFIX = b"PHONEPAD"

MOVE_SENSITIVITY = 1.6   # multiplier applied to pointer-move deltas
SCROLL_SENSITIVITY = 1.0

mouse = MouseController()
keyboard = KeyboardController()

# Live, thread-safe state shared with the GUI.
_state_lock = threading.Lock()
_clients = 0

SPECIAL_KEYS = {
    "backspace": Key.backspace,
    "enter": Key.enter,
    "tab": Key.tab,
    "esc": Key.esc,
    "space": Key.space,
    "up": Key.up,
    "down": Key.down,
    "left": Key.left,
    "right": Key.right,
    "home": Key.home,
    "end": Key.end,
    "delete": Key.delete,
}


def local_ip():
    """Best-effort local LAN IP of this machine."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]
    except Exception:
        return "127.0.0.1"
    finally:
        s.close()


def client_count():
    with _state_lock:
        return _clients


def _add_client(delta):
    global _clients
    with _state_lock:
        _clients += delta


# ---- Command handling ------------------------------------------------------

def handle_command(line):
    """Execute a single command line coming from the phone."""
    if not line:
        return
    cmd, _, rest = line.partition(" ")

    if cmd == "M":
        try:
            dx, dy = rest.split()
            # Tolerate comma decimal separators from locale-specific clients.
            mouse.move(int(round(float(dx.replace(",", ".")) * MOVE_SENSITIVITY)),
                       int(round(float(dy.replace(",", ".")) * MOVE_SENSITIVITY)))
        except ValueError:
            pass
    elif cmd == "S":
        try:
            dx, dy = rest.split()
            mouse.scroll(int(round(float(dx.replace(",", ".")) * SCROLL_SENSITIVITY)),
                         int(round(float(dy.replace(",", ".")) * SCROLL_SENSITIVITY)))
        except ValueError:
            pass
    elif cmd == "LC":
        mouse.click(Button.left)
    elif cmd == "RC":
        mouse.click(Button.right)
    elif cmd == "MC":
        mouse.click(Button.middle)
    elif cmd == "DC":
        mouse.click(Button.left, 2)
    elif cmd == "LD":
        mouse.press(Button.left)
    elif cmd == "LU":
        mouse.release(Button.left)
    elif cmd == "K":
        keyboard.type(rest)
    elif cmd == "SK":
        key = SPECIAL_KEYS.get(rest.strip().lower())
        if key is not None:
            keyboard.press(key)
            keyboard.release(key)


def serve_client(conn, addr):
    conn.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
    _add_client(1)
    buffer = b""
    try:
        with conn:
            while True:
                data = conn.recv(4096)
                if not data:
                    break
                buffer += data
                while b"\n" in buffer:
                    line, _, buffer = buffer.partition(b"\n")
                    try:
                        handle_command(line.decode("utf-8").strip())
                    except Exception:
                        pass
    except OSError:
        pass
    finally:
        _add_client(-1)


def tcp_server():
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind(("0.0.0.0", TCP_PORT))
    srv.listen(2)
    while True:
        try:
            conn, addr = srv.accept()
        except OSError:
            break
        threading.Thread(target=serve_client, args=(conn, addr),
                         daemon=True).start()


def discovery_responder():
    """Answer UDP discovery broadcasts so the phone can auto-find this PC."""
    udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    udp.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    udp.bind(("0.0.0.0", DISCOVERY_PORT))
    hostname = socket.gethostname()
    while True:
        try:
            data, addr = udp.recvfrom(1024)
            if data.strip() == DISCOVERY_MAGIC:
                reply = b"%s:%s:%d" % (DISCOVERY_REPLY_PREFIX,
                                       hostname.encode("utf-8"), TCP_PORT)
                udp.sendto(reply, addr)
        except Exception:
            time.sleep(0.1)


def start_network():
    """Spin up the TCP + discovery servers as daemon threads."""
    threading.Thread(target=tcp_server, daemon=True).start()
    threading.Thread(target=discovery_responder, daemon=True).start()


# ---- Tray icon -------------------------------------------------------------

def make_tray_image():
    """A small touchpad glyph for the system tray (generated, no asset files)."""
    from PIL import Image, ImageDraw
    img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([6, 12, 58, 52], radius=10,
                        fill=(18, 18, 20, 255), outline=(61, 220, 132, 255), width=3)
    d.line([32, 30, 32, 46], fill=(61, 220, 132, 255), width=3)
    return img


# ---- GUI -------------------------------------------------------------------

class PhonePadApp:
    BG = "#0b0b0d"
    CARD = "#16161a"
    FG = "#f2f2f4"
    MUTED = "#8a8a92"
    ACCENT = "#3ddc84"
    DANGER = "#ff5c5c"

    def __init__(self):
        import tkinter as tk
        self.tk = tk
        self.ip = local_ip()

        self.root = tk.Tk()
        self.root.title("PhonePad")
        self.root.configure(bg=self.BG)
        self.root.geometry("340x300")
        self.root.resizable(False, False)
        self._build_ui()

        # Closing with the X hides to tray instead of quitting.
        self.root.protocol("WM_DELETE_WINDOW", self.hide_window)

        # Tray icon (runs in its own thread).
        import pystray
        self.icon = pystray.Icon(
            "phonepad",
            make_tray_image(),
            "PhonePad server",
            menu=pystray.Menu(
                pystray.MenuItem("Show PhonePad", self._tray_show, default=True),
                pystray.MenuItem("Quit", self._tray_quit),
            ),
        )
        threading.Thread(target=self.icon.run, daemon=True).start()

        start_network()
        self._refresh()

    def _build_ui(self):
        tk = self.tk
        pad = {"padx": 20}

        tk.Label(self.root, text="PhonePad", bg=self.BG, fg=self.FG,
                 font=("Segoe UI Semibold", 20)).pack(anchor="w", pady=(18, 0), **pad)
        tk.Label(self.root, text="Phone touchpad server", bg=self.BG, fg=self.MUTED,
                 font=("Segoe UI", 10)).pack(anchor="w", **pad)

        card = tk.Frame(self.root, bg=self.CARD)
        card.pack(fill="x", pady=14, **pad)

        self.status_lbl = tk.Label(card, text="● Running", bg=self.CARD, fg=self.ACCENT,
                                   font=("Segoe UI Semibold", 12))
        self.status_lbl.pack(anchor="w", padx=14, pady=(12, 2))

        tk.Label(card, text=f"This PC IP:  {self.ip}", bg=self.CARD, fg=self.FG,
                 font=("Consolas", 11)).pack(anchor="w", padx=14)
        tk.Label(card, text=f"Port:  {TCP_PORT}", bg=self.CARD, fg=self.FG,
                 font=("Consolas", 11)).pack(anchor="w", padx=14)
        self.clients_lbl = tk.Label(card, text="Phones connected:  0", bg=self.CARD,
                                    fg=self.MUTED, font=("Segoe UI", 10))
        self.clients_lbl.pack(anchor="w", padx=14, pady=(2, 12))

        btns = tk.Frame(self.root, bg=self.BG)
        btns.pack(fill="x", side="bottom", pady=16, **pad)

        self._make_button(btns, "Hide to tray", self.hide_window,
                          self.CARD, self.FG).pack(side="left")
        self._make_button(btns, "Quit", self.quit_app,
                          self.DANGER, "#1a0d0d").pack(side="right")

    def _make_button(self, parent, text, cmd, bg, fg):
        return self.tk.Button(
            parent, text=text, command=cmd, bg=bg, fg=fg,
            activebackground=bg, activeforeground=fg, relief="flat", bd=0,
            font=("Segoe UI Semibold", 11), padx=18, pady=9, cursor="hand2",
        )

    def _refresh(self):
        n = client_count()
        self.clients_lbl.config(text=f"Phones connected:  {n}")
        self.status_lbl.config(
            text="● Connected" if n else "● Running",
            fg=self.ACCENT,
        )
        self.root.after(1000, self._refresh)

    # ---- window / tray actions ----
    def hide_window(self):
        self.root.withdraw()

    def show_window(self):
        self.root.deiconify()
        self.root.lift()
        self.root.focus_force()

    def quit_app(self):
        try:
            self.icon.stop()
        except Exception:
            pass
        self.root.destroy()

    # Tray callbacks run on the pystray thread; marshal to the Tk thread.
    def _tray_show(self, icon=None, item=None):
        self.root.after(0, self.show_window)

    def _tray_quit(self, icon=None, item=None):
        self.root.after(0, self.quit_app)

    def run(self):
        self.root.mainloop()


def main():
    PhonePadApp().run()


if __name__ == "__main__":
    main()

import tkinter as tk
from PIL import Image, ImageTk
import requests
import io
import threading
import time
import os

from serial_device import SerialDevice
from config import DEVICE_CONFIGS, DEVICE_ICONS, HTTP_ENDPOINT, OTHER_ICONS
from db import init_db

def resource_path(rel_path):
    base = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base, rel_path)

PLACEHOLDER_ICON = OTHER_ICONS.get("place_holder", "images/placeholder.png")
FAVICON_ICON = OTHER_ICONS.get("maincontroller", "images/maincontroller.png")

THEMES = {
    "dark": {
        "bg": "#181b28", "panel_bg": "#23253A", "card_bg": "#fff", "card_border": "#23253A",
        "fg": "#222", "title": "#09e6e6", "subtitle": "#b6bdd3",
        "accent": "#12a77d", "unavailable": "#ff4343",
        "button_bg": "#3570d8", "button_fg": "#fff", "btn_active": "#2e57dd",
        "dot_on": "#19d36a", "dot_off": "#ff4343",
        "result": "#11ae5d", "readonly": "#f05d5d", "readonly_bg": "#fbecec",
        "status_warn": "#ffcc00"
    },
    "light": {
        "bg": "#f6f8fc", "panel_bg": "#fff", "card_bg": "#fff", "card_border": "#cfd7e5",
        "fg": "#222", "title": "#089fe3", "subtitle": "#6c7b93",
        "accent": "#16c375", "unavailable": "#e33a2b",
        "button_bg": "#3570d8", "button_fg": "#fff", "btn_active": "#4281ed",
        "dot_on": "#18d363", "dot_off": "#e33a2b",
        "result": "#11905e", "readonly": "#d3322a", "readonly_bg": "#f5ebeb",
        "status_warn": "#e6a91f"
    }
}

def maximize_window(root):
    try:
        root.state('zoomed')
    except Exception:
        try:
            root.attributes('-zoomed', True)
        except Exception:
            root.attributes('-fullscreen', True)

def get_icon(path_or_url, size=(44, 44)):
    placeholder = resource_path(PLACEHOLDER_ICON)
    try:
        if path_or_url and path_or_url.startswith("http"):
            resp = requests.get(path_or_url, timeout=4)
            img = Image.open(io.BytesIO(resp.content)).convert("RGBA")
        elif path_or_url and os.path.exists(resource_path(path_or_url)):
            img = Image.open(resource_path(path_or_url)).convert("RGBA")
        elif placeholder and os.path.exists(placeholder):
            img = Image.open(placeholder).convert("RGBA")
        else:
            raise FileNotFoundError("No icon file found for path: %s" % path_or_url)
    except Exception as e:
        print(f"[ICON] Error loading '{path_or_url}': {e}")
        if placeholder and os.path.exists(placeholder):
            img = Image.open(placeholder).convert("RGBA")
        else:
            img = Image.new("RGBA", size, (180, 180, 180, 255))
    img = img.resize(size, Image.LANCZOS)
    return ImageTk.PhotoImage(img)

class StatusDot(tk.Canvas):
    def __init__(self, parent, theme, **kwargs):
        super().__init__(parent, width=18, height=18, highlightthickness=0, bg=theme["card_bg"], **kwargs)
        self.theme = theme
        self.available = False
        self.draw()

    def set_available(self, available):
        self.available = available
        self.draw()

    def set_theme(self, theme):
        self.theme = theme
        self.configure(bg=theme["card_bg"])
        self.draw()

    def draw(self):
        self.delete("all")
        color = self.theme['dot_on'] if self.available else self.theme['dot_off']
        self.create_oval(4, 4, 16, 16, fill=color, outline=color)

class DeviceCard(tk.Frame):
    def __init__(self, parent, device, icon_img=None, theme=THEMES["dark"]):
        super().__init__(parent, width=340, height=140, bg=theme["card_bg"], highlightthickness=2)
        self.device = device
        self.theme = theme
        self.icon_img = icon_img
        self._loading = False
        self.grid_propagate(False)
        self._build_card()

    def _build_card(self):
        self.configure(bg=self.theme["card_bg"], highlightbackground=self.theme["card_border"], highlightcolor=self.theme["card_border"])
        # Top Row: Icon, Name, Status Dot
        top = tk.Frame(self, bg=self.theme["card_bg"])
        top.pack(fill="x", pady=(12, 3), padx=14)
        if self.icon_img:
            tk.Label(top, image=self.icon_img, bg=self.theme["card_bg"]).pack(side="left", padx=(0, 8))
        else:
            tk.Label(top, text="🟡", font=("Segoe UI", 20), bg=self.theme["card_bg"]).pack(side="left", padx=(0, 8))

        self.name_lbl = tk.Label(top, text=self.device.name, font=("Segoe UI", 15, "bold"),
                                 fg=self.theme["accent"], bg=self.theme["card_bg"])
        self.name_lbl.pack(side="left", padx=(0, 10))
        self.status_dot = StatusDot(top, self.theme)
        self.status_dot.pack(side="right", padx=(0, 2))

        # Status
        self.status_lbl = tk.Label(self, text="Unavailable — disconnected", font=("Segoe UI", 11),
                                   fg=self.theme["unavailable"], bg=self.theme["card_bg"])
        self.status_lbl.pack(anchor="w", padx=18, pady=(4, 0))

        # Result/Error/Readonly (wrap in the card, never expand card size)
        self.result_lbl = tk.Label(self, text="", font=("Segoe UI", 11, "bold"),
                                   fg=self.theme["result"], bg=self.theme["card_bg"],
                                   wraplength=290, justify="left", anchor="w")
        self.result_lbl.pack(anchor="w", padx=18, pady=(1, 0), fill="x")

    def set_theme(self, theme):
        self.theme = theme
        self.configure(bg=theme["card_bg"], highlightbackground=theme["card_border"], highlightcolor=theme["card_border"])
        for w in self.winfo_children():
            if isinstance(w, tk.Frame):
                w.configure(bg=theme["card_bg"])
        self.name_lbl.configure(fg=theme["accent"], bg=theme["card_bg"])
        self.status_lbl.configure(bg=theme["card_bg"], fg=theme["unavailable"])
        self.result_lbl.configure(bg=theme["card_bg"])
        self.status_dot.set_theme(theme)

    def update_status(self):
        available = self.device.serial is not None and self.device.serial.is_open and self.device.available
        self.status_dot.set_available(available)
        if available:
            self.status_lbl.configure(text="Connected — available", fg=self.theme["accent"])
        else:
            self.status_lbl.configure(text="Unavailable — disconnected", fg=self.theme["unavailable"])
        res = self.device.last_result
        if self._loading:
            self.result_lbl.configure(text="Loading...", fg=self.theme["subtitle"])
        elif res:
            if "weight_display" in res:
                self.result_lbl.configure(text=res["weight_display"], fg=self.theme["result"])
            elif "weight" in res:
                self.result_lbl.configure(text=f"Weight = {res['weight']}", fg=self.theme["result"])
            elif "error" in res:
                txt = res["error"]
                if "readonly" in txt or "read only" in txt:
                    self.result_lbl.configure(text=txt, fg=self.theme["readonly"], bg=self.theme["readonly_bg"])
                else:
                    self.result_lbl.configure(text=txt, fg=self.theme["unavailable"], bg=self.theme["card_bg"])
            else:
                self.result_lbl.configure(text="No value", fg=self.theme["fg"], bg=self.theme["card_bg"])
        else:
            self.result_lbl.configure(text="", fg=self.theme["fg"], bg=self.theme["card_bg"])

    def show_loading(self, is_loading=True):
        self._loading = is_loading
        self.update_status()

class GoldControllerApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("GoldController")
        maximize_window(self)
        # Set favicon/icon for the window
        icon_path = resource_path(FAVICON_ICON)
        if os.path.exists(icon_path):
            try:
                self.icon_img = ImageTk.PhotoImage(Image.open(icon_path).resize((48, 48)))
                self.iconphoto(True, self.icon_img)
            except Exception as e:
                print(f"[FAVICON] Error loading favicon '{icon_path}': {e}")

        self.theme_name = "dark"
        self.theme = THEMES[self.theme_name]

        init_db()
        self.icon_imgs = {}
        for k, url in DEVICE_ICONS.items():
            self.icon_imgs[k] = get_icon(url)  # returns a Tk image object

        self.devices = [SerialDevice(**cfg) for cfg in DEVICE_CONFIGS]
        self.device_cards = []
        self.build_ui()
        self.after(800, self.auto_initial_check)
        self.refresh_cards_loop()

    def build_ui(self):
        self.configure(bg=self.theme["bg"])
        # ---- HEADER ----
        header = tk.Frame(self, bg=self.theme["bg"])
        header.pack(fill="x", pady=(15, 0))

        # Centered block for title and subtitle
        block = tk.Frame(header, bg=self.theme["panel_bg"], height=96)
        block.pack(side="top", pady=(0, 0), padx=70, fill="x")
        block.grid_columnconfigure(0, weight=1)
        block.grid_rowconfigure(0, weight=1)
        # Add theme button in block (top right)
        self.theme_btn = tk.Button(block, text="🌙 Theme", command=self.toggle_theme,
                                   bg=self.theme["panel_bg"], fg=self.theme["subtitle"],
                                   font=("Segoe UI", 12, "bold"), bd=0, relief="flat", cursor="hand2",
                                   activebackground=self.theme["panel_bg"], activeforeground=self.theme["accent"])
        self.theme_btn.place(relx=1.0, x=-24, y=10, anchor="ne")
        # Title and subtitle
        tk.Label(block, text="GoldController", font=("Segoe UI", 29, "bold"),
                 fg=self.theme["title"], bg=self.theme["panel_bg"]).pack(pady=(14, 0))
        tk.Label(block, text="Real-time monitoring and control system", font=("Segoe UI", 14),
                 fg=self.theme["subtitle"], bg=self.theme["panel_bg"]).pack(pady=(2, 13))

        # ---- CARD GRID ----
        panel = tk.Frame(self, bg=self.theme["panel_bg"])
        panel.pack(fill="x", padx=60, pady=(10, 0))
        self.card_grid = tk.Frame(panel, bg=self.theme["panel_bg"])
        self.card_grid.pack(anchor="center", pady=18)
        # fill grid
        self.device_cards = []
        idx = 0
        for row in range(2):
            for col in range(3):
                if idx < len(self.devices):
                    dev = self.devices[idx]
                    card = DeviceCard(self.card_grid, dev, icon_img=self.icon_imgs.get(dev.name), theme=self.theme)
                    card.grid(row=row, column=col, padx=34, pady=18)
                    self.device_cards.append(card)
                    idx += 1
                else:
                    empty = tk.Frame(self.card_grid, width=340, height=140, bg=self.theme["panel_bg"])
                    empty.grid(row=row, column=col, padx=34, pady=18)

        # ---- BUTTONS ----
        tk.Frame(self, height=18, bg=self.theme["bg"]).pack()
        btn_bar = tk.Frame(self, bg=self.theme["bg"])
        btn_bar.pack(fill="x", padx=0, pady=(0, 18))
        btn_bar.columnconfigure(0, weight=1)
        btn_bar.columnconfigure(2, weight=1)
        self.check_btn = tk.Button(btn_bar, text="Check Now", command=self.check_all,
                                   font=("Segoe UI", 16, "bold"), width=18, height=2,
                                   bg=self.theme["button_bg"], fg=self.theme["button_fg"],
                                   activebackground=self.theme["btn_active"], bd=0, relief="ridge")
        self.check_btn.grid(row=0, column=0, padx=18)
        tk.Frame(btn_bar, width=60, bg=self.theme["bg"]).grid(row=0, column=1)
        self.sync_btn = tk.Button(btn_bar, text="Sync to Server", command=self.sync_all,
                                  font=("Segoe UI", 16, "bold"), width=18, height=2,
                                  bg=self.theme["button_bg"], fg=self.theme["button_fg"],
                                  activebackground=self.theme["btn_active"], bd=0, relief="ridge")
        self.sync_btn.grid(row=0, column=2, padx=18)

    def set_theme_all(self):
        self.theme = THEMES[self.theme_name]
        self.configure(bg=self.theme["bg"])
        # Update theme button (now inside the block panel)
        self.theme_btn.configure(bg=self.theme["panel_bg"], fg=self.theme["subtitle"], activebackground=self.theme["panel_bg"], activeforeground=self.theme["accent"])
        for w in self.winfo_children():
            if isinstance(w, tk.Frame):
                w.configure(bg=self.theme["bg"])
        # Cards
        for card in self.device_cards:
            card.set_theme(self.theme)
        self.check_btn.configure(bg=self.theme["button_bg"], fg=self.theme["button_fg"], activebackground=self.theme["btn_active"])
        self.sync_btn.configure(bg=self.theme["button_bg"], fg=self.theme["button_fg"], activebackground=self.theme["btn_active"])
        # Panels
        for panel in [self.card_grid.master, self.card_grid]:
            panel.configure(bg=self.theme["panel_bg"])
        for child in self.card_grid.winfo_children():
            if isinstance(child, tk.Frame) and not hasattr(child, "device"):
                child.configure(bg=self.theme["panel_bg"])

    def toggle_theme(self):
        self.theme_name = "light" if self.theme_name == "dark" else "dark"
        self.set_theme_all()

    def refresh_cards_loop(self):
        for card in self.device_cards:
            card.update_status()
        self.after(400, self.refresh_cards_loop)

    def auto_initial_check(self):
        def initial_sequence():
            for dev, card in zip(self.devices, self.device_cards):
                dev.send_command("B")
                time.sleep(0.6)
            time.sleep(1)
            for dev, card in zip(self.devices, self.device_cards):
                if dev.serial and dev.serial.is_open and dev.available:
                    card.show_loading(True)
                    dev.send_command("S")
                    t0 = time.time()
                    while time.time() - t0 < 2.2:
                        if dev.last_result and "weight_display" in dev.last_result:
                            break
                        time.sleep(0.15)
                    card.show_loading(False)
        threading.Thread(target=initial_sequence, daemon=True).start()

    def check_all(self):
        def check_sequence():
            for dev, card in zip(self.devices, self.device_cards):
                if dev.serial and dev.serial.is_open and dev.available:
                    card.show_loading(True)
                    dev.send_command("S")
                else:
                    card.show_loading(False)
            for dev, card in zip(self.devices, self.device_cards):
                if dev.serial and dev.serial.is_open and dev.available:
                    t0 = time.time()
                    while time.time() - t0 < 2.2:
                        if dev.last_result and "weight_display" in dev.last_result:
                            break
                        time.sleep(0.15)
                    card.show_loading(False)
                else:
                    card.show_loading(False)
        threading.Thread(target=check_sequence, daemon=True).start()

    def sync_all(self):
        def sync_sequence():
            results = {}
            for dev in self.devices:
                if dev.serial and dev.serial.is_open and dev.available:
                    dev.send_command("P")
                    t0 = time.time()
                    while time.time() - t0 < 3:
                        if dev.last_result:
                            break
                        time.sleep(0.2)
                    results[dev.name] = dev.last_result
            try:
                payload = {
                    "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
                    "results": results
                }
                resp = requests.post(HTTP_ENDPOINT, json=payload, timeout=5)
                for card in self.device_cards:
                    card.status_lbl.config(text=f"Sync: {resp.status_code}",
                                          fg=self.theme["accent"] if resp.status_code == 200 else self.theme["status_warn"])
            except Exception as ex:
                for card in self.device_cards:
                    card.status_lbl.config(text=f"HTTP error: {ex}", fg=self.theme["unavailable"])
        threading.Thread(target=sync_sequence, daemon=True).start()

    def on_closing(self):
        for dev in getattr(self, "devices", []):
            dev.close()
        self.destroy()

if __name__ == "__main__":
    GoldControllerApp().mainloop()

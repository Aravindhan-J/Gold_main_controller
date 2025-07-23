import kivy
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.widget import Widget
from kivy.uix.image import AsyncImage
from kivy.graphics import Color, RoundedRectangle, Ellipse
from kivy.clock import Clock, mainthread
from kivy.core.window import Window
import json
import threading
import time
from serial_device import SerialDevice
from config import DEVICE_CONFIGS, DEVICE_ICONS, HTTP_ENDPOINT, OTHER_ICONS
from db import init_db

Window.maximize()
Window.softinput_mode = "below_target"

class StatusDot(Widget):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.size_hint = (None, None)
        self.size = (17, 17)
        self.available = False
        self.bind(pos=self.update_dot, size=self.update_dot)
    def set_available(self, available):
        self.available = available
        self.update_dot()
    def update_dot(self, *args):
        self.canvas.clear()
        with self.canvas:
            Color(0.19, 0.93, 0.45, 1) if self.available else Color(1, 0.27, 0.23, 1)
            Ellipse(pos=self.pos, size=self.size)

class DeviceCard(BoxLayout):
    def __init__(self, device: SerialDevice, icon_url, **kwargs):
        super().__init__(orientation='vertical', padding=[18,14,18,16], spacing=5, size_hint=(None, None), width=330, height=190, **kwargs)
        self.device = device
        self.icon_url = icon_url
        with self.canvas.before:
            Color(0.13, 0.14, 0.21, 1)
            self.bg = RoundedRectangle(radius=[16], pos=self.pos, size=self.size)
        self.bind(pos=self._update_bg, size=self._update_bg)
        top = BoxLayout(orientation='horizontal', size_hint_y=None, height=38)
        self.icon = AsyncImage(source=self.icon_url, size_hint=(None, None), size=(36, 36))
        self.name_lbl = Label(text=f"[b]{device.name}[/b]", markup=True, font_size=21, color=(0.14,0.97,1,1), size_hint=(1,1), halign='left', valign='middle')
        self.name_lbl.bind(size=self.name_lbl.setter('text_size'))
        self.dot = StatusDot()
        top.add_widget(self.icon)
        top.add_widget(self.name_lbl)
        top.add_widget(self.dot)
        self.status_lbl = Label(text="Unavailable — disconnected", font_size=15, color=(1,0.27,0.27,1), size_hint_y=None, height=26, halign='left', valign='middle')
        self.status_lbl.bind(size=self.status_lbl.setter('text_size'))

        # Add result label and loading image
        self.result_label = Label(text="", font_size=17, color=(0.92,1,0.92,1), size_hint_y=None, height=34, halign='left', valign='middle', markup=True)
        self.result_label.bind(size=self.result_label.setter('text_size'))

        self.loading_img = AsyncImage(
            source=OTHER_ICONS["loading"],
            size_hint=(None, None),
            size=(38, 38),
            opacity=0  # Hidden by default
        )

        self.loading = False
        self.add_widget(top)
        self.add_widget(self.status_lbl)
        self.add_widget(self.result_label)
        self.add_widget(self.loading_img)
        self.add_widget(Widget())

        self.result_label.opacity = 1
        self.loading_img.opacity = 0

    def _update_bg(self, *args):
        self.bg.pos = self.pos
        self.bg.size = self.size

    @mainthread
    def show_loading(self, is_loading=True):
        self.loading = is_loading
        if is_loading:
            self.result_label.opacity = 0
            self.loading_img.opacity = 1
        else:
            self.loading_img.opacity = 0
            self.result_label.opacity = 1
            self.refresh_status()

    def refresh_status(self, dt=None):
        available = self.device.serial is not None and self.device.serial.is_open and self.device.available
        self.dot.set_available(available)
        # Status
        if available:
            self.status_lbl.text = "Connected — available"
            self.status_lbl.color = (0.13, 0.83, 0.36, 1)
        else:
            self.status_lbl.text = "Unavailable — disconnected"
            self.status_lbl.color = (1,0.3,0.3,1)
        # Result or error
        if self.loading:
            return  # Don't show value while loading
        if self.device.last_result:
            if "weight_display" in self.device.last_result:
                self.result_label.text = f"[color=#48ff78]{self.device.last_result['weight_display']}[/color]"
                self.result_label.color = (0.29, 1, 0.47, 1)
            elif "weight" in self.device.last_result:
                self.result_label.text = f"[color=#48ff78]Weight = {self.device.last_result['weight']}[/color]"
                self.result_label.color = (0.29, 1, 0.47, 1)
            elif "error" in self.device.last_result:
                self.result_label.text = f"[color=#ff4444]{self.device.last_result['error']}[/color]"
                self.result_label.color = (1, 0.2, 0.2, 1)
            else:
                self.result_label.text = "[color=#cccccc]No value[/color]"
                self.result_label.color = (0.92, 1, 0.92, 1)
        else:
            self.result_label.text = ""
            self.result_label.color = (0.92, 1, 0.92, 1)

class MainLayout(BoxLayout):
    def __init__(self, device_cards, check_btn, sync_btn, **kwargs):
        super().__init__(orientation='vertical', spacing=10, padding=[36,46,56,10], **kwargs)
        # Header (centered)
        topbar = BoxLayout(orientation='horizontal', size_hint_y=None, height=62, padding=[0,0,0,0])
        titlecol = BoxLayout(orientation='vertical', size_hint=(1,1))
        title = Label(text="[b][color=#485074]GoldController[/color][/b]", markup=True, font_size=29, color=(0.4,0.45,0.48,1), size_hint=(1,1), halign='center')
        subtitle = Label(text="Real-time monitoring and control system", font_size=16, color=(0.65,0.67,0.72,1), size_hint=(1,1), halign='center')
        titlecol.add_widget(title)
        titlecol.add_widget(subtitle)
        topbar.add_widget(Widget(size_hint_x=0.5))
        topbar.add_widget(titlecol)
        topbar.add_widget(Widget(size_hint_x=0.5))
        self.add_widget(topbar)
        self.add_widget(Widget(size_hint_y=None, height=7))
        # Grid for cards (3x2, aligned top)
        grid = GridLayout(cols=3, rows=2, spacing=26, size_hint=(1, None), height=400)
        for i, card in enumerate(device_cards):
            grid.add_widget(card)
        if len(device_cards) < 6:
            for _ in range(6-len(device_cards)):
                grid.add_widget(Widget())
        self.add_widget(grid)
        self.add_widget(Widget())
        # Sticky footer for action buttons (plain, no icon)
        footer = BoxLayout(orientation='horizontal', size_hint_y=None, height=60, spacing=18, padding=[0,0,0,0])
        footer.add_widget(Widget())
        footer.add_widget(check_btn)
        footer.add_widget(sync_btn)
        footer.add_widget(Widget())
        self.add_widget(footer)
        for card in device_cards:
            Clock.schedule_interval(card.refresh_status, 0.45)

class GoldControllerApp(App):
    def build(self):
        init_db()
        self.is_dark = True
        self.theme = {
            "dark": {"bg": [0.10,0.13,0.17,1], "fg": [1,1,1,1]},
            "light": {"bg": [1,1,1,1], "fg": [0.13,0.16,0.20,1]}
        }
        Window.clearcolor = self.theme["dark"]["bg"]
        Window.maximize()
        self.devices = []
        for cfg in DEVICE_CONFIGS:
            dev = SerialDevice(port=cfg["port"], baudrate=cfg["baudrate"], name=cfg["name"])
            self.devices.append(dev)
        self.device_cards = []
        for dev in self.devices:
            icon_url = DEVICE_ICONS.get(dev.name)
            self.device_cards.append(DeviceCard(dev, icon_url))
        self.check_btn = Button(text="Check Now", font_size=18, size_hint=(None,None), width=185, height=50,
                                background_color=(0.22,0.48,0.99,1), color=(1,1,1,1), background_normal='')
        self.sync_btn = Button(text="Sync to Server", font_size=18, size_hint=(None,None), width=185, height=50,
                               background_color=(.97,.97,.97,1), color=(.18,.22,.35,1), background_normal='')
        self.check_btn.bind(on_release=self.check_all)
        self.sync_btn.bind(on_release=self.sync_all)
        self.root_layout = MainLayout(self.device_cards, self.check_btn, self.sync_btn)
        # On load, check all devices and fetch value for available ones
        Clock.schedule_once(lambda dt: self.auto_initial_check(), 0.8)
        return self.root_layout

    def auto_initial_check(self):
        # First, check all for availability and value
        def initial_sequence():
            for dev, card in zip(self.devices, self.device_cards):
                dev.send_command("B")
                time.sleep(0.6)
            time.sleep(1)
            for dev, card in zip(self.devices, self.device_cards):
                if dev.serial and dev.serial.is_open and dev.available:
                    card.show_loading(True)
                    dev.send_command("S")
                    # Wait until we get a value (max 2 seconds)
                    t0 = time.time()
                    while time.time() - t0 < 2.2:
                        if dev.last_result and "weight_display" in dev.last_result:
                            break
                        time.sleep(0.15)
                    card.show_loading(False)
        threading.Thread(target=initial_sequence, daemon=True).start()

    def check_all(self, instance):
        def check_sequence():
            for dev, card in zip(self.devices, self.device_cards):
                if dev.serial and dev.serial.is_open and dev.available:
                    card.show_loading(True)  # Only set loading for available devices!
                    dev.send_command("S")
                else:
                    card.show_loading(False) # Hide loading for unavailable cards

            # Wait for results (max 2s per device)
            for dev, card in zip(self.devices, self.device_cards):
                if dev.serial and dev.serial.is_open and dev.available:
                    t0 = time.time()
                    while time.time() - t0 < 2.2:
                        if dev.last_result and "weight_display" in dev.last_result:
                            break
                        time.sleep(0.15)
                    card.show_loading(False)
                else:
                    card.show_loading(False) # Ensure loading stays off for unavailable

        threading.Thread(target=check_sequence, daemon=True).start()

    def sync_all(self, instance):
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
                import requests
                payload = {
                    "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
                    "results": results
                }
                resp = requests.post(HTTP_ENDPOINT, json=payload, timeout=5)
                for card in self.device_cards:
                    card.status_lbl.text = f"Sync: {resp.status_code}"
                    card.status_lbl.color = (0.13, 0.83, 0.36, 1) if resp.status_code == 200 else (1,0.7,0.1,1)
            except Exception as ex:
                for card in self.device_cards:
                    card.status_lbl.text = f"HTTP error: {ex}"
                    card.status_lbl.color = (1,0.27,0.27,1)
        threading.Thread(target=sync_sequence, daemon=True).start()

    def on_stop(self):
        for dev in getattr(self, "devices", []):
            dev.close()

if __name__ == "__main__":
    GoldControllerApp().run()

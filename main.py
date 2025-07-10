import kivy
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.widget import Widget
from kivy.graphics import Color, Ellipse
from kivy.clock import Clock
from kivy.core.window import Window

import json
import threading
import time
import requests
from serial_device import SerialDevice
from config import DEVICE_CONFIGS, HTTP_ENDPOINT
from db import init_db

class StatusDot(Widget):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.size_hint = (None, None)
        self.size = (18, 18)
        self.available = False
        self.bind(pos=self.update_dot, size=self.update_dot)
    def set_available(self, available):
        self.available = available
        self.update_dot()
    def update_dot(self, *args):
        self.canvas.clear()
        with self.canvas:
            Color(0.17, 0.83, 0.36, 1) if self.available else Color(1, 0.27, 0.23, 1)
            Ellipse(pos=self.pos, size=self.size)

class DeviceCard(BoxLayout):
    def __init__(self, device: SerialDevice, **kwargs):
        super().__init__(orientation='vertical', padding=10, spacing=8, **kwargs)
        self.device = device
        self.size_hint = (1, None)
        self.height = 170

        head = BoxLayout(orientation='horizontal', size_hint=(1, None), height=26)
        self.name_lbl = Label(
            text=f"[b]{device.name}[/b]", font_size=17,
            color=(0.18, 0.95, 1, 1), markup=True, halign="left", valign="middle", size_hint_x=0.88
        )
        self.dot = StatusDot()
        head.add_widget(self.name_lbl)
        head.add_widget(self.dot)

        self.status_lbl = Label(text="Unavailable", font_size=13, color=(1,0.27,0.27,1), markup=False, size_hint_y=None, height=20)
        self.result_txt = TextInput(text="", readonly=True, background_color=(.13,.14,.21,1), foreground_color=(1,1,1,1), font_size=13, size_hint_y=None, height=45)

        self.add_widget(head)
        self.add_widget(self.status_lbl)
        self.add_widget(self.result_txt)

        Clock.schedule_interval(self.refresh_status, 0.5)
        self.refresh_status(0)

    def refresh_status(self, dt):
        available = self.device.serial is not None and self.device.serial.is_open
        self.dot.set_available(available)
        if available:
            self.status_lbl.text = "Connected"
            self.status_lbl.color = (0.13, 0.83, 0.36, 1)
        else:
            self.status_lbl.text = "Unavailable"
            self.status_lbl.color = (1,0.27,0.27,1)
        if self.device.status:
            self.status_lbl.text += f" — {self.device.status}"
        self.result_txt.text = json.dumps(self.device.last_result, indent=2) if self.device.last_result else ""

class ThemeButton(Button):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.size_hint = (None, None)
        self.size = (27, 27)
        self.font_size = 16
        self.text = "🌙"
        self.background_normal = ''
        self.background_color = (0.12,0.18,0.35,1)
        self.color = (1,1,1,1)
        self.pos_hint = {'top': 1, 'right': 1}
        self.bind(on_release=self.toggle_theme)
        self.is_dark = True
    def toggle_theme(self, *args):
        self.is_dark = not self.is_dark
        self.text = "☀️" if not self.is_dark else "🌙"
        App.get_running_app().toggle_theme(self.is_dark)

class ResponsiveCards(BoxLayout):
    def __init__(self, device_cards, **kwargs):
        super().__init__(orientation='horizontal', spacing=12, padding=[6,6,6,6], **kwargs)
        self.cards = device_cards
        self.orientation = 'horizontal' if Window.width > 880 else 'vertical'
        for card in device_cards:
            self.add_widget(card)
        Window.bind(on_resize=self.on_resize)
        self.on_resize(Window, Window.width, Window.height)
    def on_resize(self, win, w, h):
        self.orientation = 'horizontal' if w > 880 else 'vertical'

class MainLayout(BoxLayout):
    def __init__(self, device_cards, check_btn, sync_btn, theme_btn, **kwargs):
        super().__init__(orientation='vertical', spacing=5, padding=[10,10,10,10], **kwargs)
        # Top bar: theme button right
        top = BoxLayout(orientation='horizontal', size_hint_y=None, height=38)
        top.add_widget(Widget())
        top.add_widget(theme_btn)
        self.add_widget(top)
        # Device cards area (responsive)
        self.cards_area = ResponsiveCards(device_cards)
        self.add_widget(self.cards_area)
        # Bottom sticky bar
        sticky = BoxLayout(orientation='horizontal', size_hint_y=None, height=54, spacing=14, padding=[0,4,0,4])
        sticky.add_widget(Widget())
        sticky.add_widget(check_btn)
        sticky.add_widget(sync_btn)
        sticky.add_widget(Widget())
        self.add_widget(sticky)
        Window.bind(on_resize=self.on_resize)
    def on_resize(self, win, w, h):
        self.cards_area.on_resize(win, w, h)

class GoldControllerApp(App):
    def build(self):
        init_db()
        self.is_dark = True
        self.theme = {
            "dark": {
                "bg": [0.09,0.10,0.18,1],
                "fg": [1,1,1,1]
            },
            "light": {
                "bg": [1,1,1,1],
                "fg": [0.13,0.16,0.20,1]
            }
        }
        Window.clearcolor = self.theme["dark"]["bg"]
        self.devices = [SerialDevice(port=cfg["port"], baudrate=cfg["baudrate"], name=cfg["name"]) for cfg in DEVICE_CONFIGS]
        self.device_cards = [DeviceCard(dev) for dev in self.devices]
        # Buttons (shared for all devices)
        self.check_btn = Button(text="Check Now", font_size=16, size_hint=(None,None), width=140, height=40,
                                background_color=(0.17,0.42,0.85,1), color=(1,1,1,1))
        self.sync_btn = Button(text="Sync to Server", font_size=16, size_hint=(None,None), width=150, height=40,
                               background_color=(0.14,0.68,0.38,1), color=(1,1,1,1))
        self.theme_btn = ThemeButton()
        self.check_btn.bind(on_release=self.check_all)
        self.sync_btn.bind(on_release=self.sync_all)
        self.root_layout = MainLayout(self.device_cards, self.check_btn, self.sync_btn, self.theme_btn)
        return self.root_layout

    def check_all(self, instance):
        def check_sequence():
            for dev in self.devices:
                dev.send_command("S")
                time.sleep(1.1)
        threading.Thread(target=check_sequence, daemon=True).start()

    def sync_all(self, instance):
        def sync_sequence():
            results = {}
            for dev in self.devices:
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
                    card.status_lbl.text = f"Sync: {resp.status_code}"
                    card.status_lbl.color = (0.13, 0.83, 0.36, 1) if resp.status_code == 200 else (1,0.7,0.1,1)
            except Exception as ex:
                for card in self.device_cards:
                    card.status_lbl.text = f"HTTP error: {ex}"
                    card.status_lbl.color = (1,0.27,0.27,1)
        threading.Thread(target=sync_sequence, daemon=True).start()

    def toggle_theme(self, is_dark):
        Window.clearcolor = self.theme["dark" if is_dark else "light"]["bg"]
    def on_stop(self):
        for dev in getattr(self, "devices", []):
            dev.close()

if __name__ == "__main__":
    GoldControllerApp().run()

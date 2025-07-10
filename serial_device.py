# serial_device.py

import serial
import threading
import queue
import json
import datetime
import requests
import traceback
from config import LOGFILE, HTTP_ENDPOINT, TEST_COMMAND
from db import log_result

def log_command(cmd, device_name):
    with open(LOGFILE, "a") as f:
        f.write(f"{datetime.datetime.now().isoformat()} | {device_name} | CMD: {cmd}\n")

def send_result_http(device_name, result):
    try:
        payload = {
            "device": device_name,
            "result": result,
            "timestamp": datetime.datetime.now().isoformat(),
        }
        r = requests.post(HTTP_ENDPOINT, json=payload, timeout=5)
        return r.status_code, r.text
    except Exception as e:
        return None, str(e)

class SerialDevice(threading.Thread):
    def __init__(self, port, baudrate, name):
        super().__init__(daemon=True)
        self.port = port
        self.baudrate = baudrate
        self.name = name
        self.serial = None
        self.last_result = None
        self.status = "disconnected"
        self.available = False  # For green/red indicator
        self.cmd_queue = queue.Queue()
        self.running = True
        self._open_serial()
        self.start()

    def _open_serial(self):
        try:
            self.serial = serial.Serial(self.port, self.baudrate, timeout=1)
            self.status = "connected"
        except Exception as e:
            self.status = f"error: {e}"
            self.available = False

    def check_availability(self):
        """Send 'B' to check device is alive (updates .available/.status)."""
        if self.serial and self.serial.is_open:
            try:
                self.serial.reset_input_buffer()
                self.serial.write(TEST_COMMAND.encode('utf-8') + b'\n')
                response = self.serial.readline().decode('utf-8').strip()
                if response:
                    self.available = True
                    self.status = "available"
                else:
                    self.available = False
                    self.status = "no response"
            except Exception as e:
                self.available = False
                self.status = f"error: {e}"
        else:
            self.available = False
            self.status = "disconnected"

    def get_measurement(self):
        """Send S or SI to device, expect JSON, update .last_result/.status."""
        if self.serial and self.serial.is_open:
            try:
                self.serial.reset_input_buffer()
                # Try S, SI, si (case-insensitive, as required by your device)
                for cmd in ["S", "SI", "si"]:
                    self.serial.write(cmd.encode('utf-8') + b'\n')
                    line = self.serial.readline().decode('utf-8').strip()
                    if not line:
                        continue
                    try:
                        data = json.loads(line)
                        self.last_result = data
                        self.status = "measurement ok"
                        log_result(self.name, cmd, json.dumps(data), None)
                        return True
                    except Exception as e:
                        self.status = f"bad json: {line}"
                        log_result(self.name, cmd, None, f"JSON decode error: {line} | {e}")
                return False
            except Exception as e:
                self.status = f"error: {e}"
                log_result(self.name, 'S/SI', None, str(e))
                return False
        else:
            self.status = "disconnected"
            return False

    def get_last_json(self):
        """Send P, expect JSON, update .last_result/.status."""
        if self.serial and self.serial.is_open:
            try:
                self.serial.reset_input_buffer()
                self.serial.write(b'P\n')
                line = self.serial.readline().decode('utf-8').strip()
                if line:
                    try:
                        data = json.loads(line)
                        self.last_result = data
                        self.status = "last result ok"
                        log_result(self.name, "P", json.dumps(data), None)
                        return True
                    except Exception as e:
                        self.status = f"bad json: {line}"
                        log_result(self.name, "P", None, f"JSON decode error: {line} | {e}")
                        return False
                else:
                    self.status = "no response for P"
                    return False
            except Exception as e:
                self.status = f"error: {e}"
                log_result(self.name, "P", None, str(e))
                return False
        else:
            self.status = "disconnected"
            return False

    def run(self):
        # On startup, check availability
        self.check_availability()
        while self.running:
            try:
                try:
                    cmd = self.cmd_queue.get(timeout=0.1)
                    if cmd.upper() in ("S", "SI"):
                        self.get_measurement()
                    elif cmd.upper() == "P":
                        self.get_last_json()
                        # HTTP sync can be triggered from UI after getting last json
                    elif cmd.upper() == "B":
                        self.check_availability()
                except queue.Empty:
                    # Periodic availability check
                    self.check_availability()
                    continue
            except Exception as ex:
                self.status = f"error: {ex}"
                log_result(self.name, '', None, traceback.format_exc())

    def send_command(self, cmd):
        if self.serial and self.serial.is_open:
            self.cmd_queue.put(cmd)

    def close(self):
        self.running = False
        if self.serial and self.serial.is_open:
            self.serial.close()

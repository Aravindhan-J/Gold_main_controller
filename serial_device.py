import serial
import threading
import queue
import json
import datetime
import requests
import traceback
import re
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
        self.available = False
        self.last_error = None
        self.cmd_queue = queue.Queue()
        self.running = True
        self._open_serial()
        self.check_availability()
        self.start()

    def _open_serial(self):
        try:
            self.serial = serial.Serial(self.port, self.baudrate, timeout=1)
            self.status = "connected"
        except Exception as e:
            self.status = f"error: {e}"
            self.available = False

    def check_availability(self):
        """Check if device is available, log every check."""
        response = ""
        err = None
        if self.serial and self.serial.is_open:
            try:
                self.serial.reset_input_buffer()
                self.serial.write(b'B\n')
                response = self.serial.readline().decode('utf-8', errors='ignore').strip()
                self.available = bool(response)
                self.status = "available" if self.available else "no response"
            except Exception as e:
                self.available = False
                self.status = f"error: {e}"
                err = str(e)
        else:
            self.available = False
            self.status = "disconnected"
            err = "disconnected"

        log_result(self.name, "B", response, err)

    def get_measurement(self):
        """
        Send 'S' to device, expect 'S S      1.182 g'
        Log every attempt/result.
        """
        self.last_result = None
        self.last_error = None
        result = None
        err = None

        if self.serial and self.serial.is_open:
            try:
                self.serial.reset_input_buffer()
                self.serial.write(b'S\n')
                value = None
                for _ in range(3):
                    line = self.serial.readline().decode('utf-8', errors='ignore').strip()
                    if not line:
                        continue
                    match = re.match(r'(?:S S|S)\s*([\d.]+)\s*g', line)
                    if match:
                        value = match.group(1)
                        result = {"weight_display": f"Weight = {value} g"}
                        self.status = "measurement ok"
                        self.last_result = result
                        break
                    else:
                        # Even if line doesn't match, log it as a raw result
                        result = {"raw": line}
                        self.last_result = result
                if not value:
                    err = "Could not parse value"
                    self.status = "unexpected response"
                    self.last_result = {"error": err}
            except Exception as e:
                err = f"Device error: {e}"
                self.status = f"error: {e}"
                self.last_result = {"error": str(e)}
        else:
            err = "Device not connected"
            self.status = "disconnected"
            self.last_result = {"error": err}

        log_result(self.name, "S", self.last_result, err)
        self.last_error = err
        return err is None

    def get_last_json(self):
        """
        Send 'P' to device, expect JSON. Log every result.
        """
        self.last_result = None
        self.last_error = None
        result = None
        err = None

        if self.serial and self.serial.is_open:
            try:
                self.serial.reset_input_buffer()
                self.serial.write(b'P\n')
                line = self.serial.readline().decode('utf-8', errors='ignore').strip()
                if line:
                    try:
                        data = json.loads(line)
                        result = data
                        self.last_result = data
                        self.status = "last result ok"
                    except Exception as e:
                        err = f"JSON decode error: {line}"
                        self.status = f"bad json: {line}"
                        result = {"raw": line}
                        self.last_result = {"error": err}
                else:
                    err = "No response"
                    self.status = "no response for P"
                    self.last_result = {"error": err}
            except Exception as e:
                err = str(e)
                self.status = f"error: {e}"
                self.last_result = {"error": err}
        else:
            err = "Device not connected"
            self.status = "disconnected"
            self.last_result = {"error": err}

        log_result(self.name, "P", self.last_result, err)
        self.last_error = err
        return err is None

    def run(self):
        self.check_availability()
        while self.running:
            try:
                try:
                    cmd = self.cmd_queue.get(timeout=0.1)
                    if cmd.upper() == "S":
                        self.get_measurement()
                    elif cmd.upper() == "P":
                        self.get_last_json()
                    elif cmd.upper() == "B":
                        self.check_availability()
                    else:
                        # Log any custom/unknown command
                        log_result(self.name, cmd, "NotImplemented", "Unknown command")
                except queue.Empty:
                    self.check_availability()
                    continue
            except Exception as ex:
                self.status = f"error: {ex}"
                self.last_error = str(ex)
                self.last_result = {"error": str(ex)}
                log_result(self.name, "run-loop", self.last_result, str(ex))

    def send_command(self, cmd):
        if self.serial and self.serial.is_open:
            self.cmd_queue.put(cmd)
        else:
            # Always log attempts to send when disconnected
            log_result(self.name, cmd, "Not sent", "Device not connected")

    def close(self):
        self.running = False
        if self.serial and self.serial.is_open:
            self.serial.close()

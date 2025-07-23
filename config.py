DBFILE = "machine_results.db"
LOGFILE = "device.log"
HTTP_ENDPOINT = "http://your-server/endpoint"
TEST_COMMAND = "B" 

DEVICE_CONFIGS = [
    {"name": "Weighing",    "port": "/dev/ttyUSB0", "baudrate": 9600},
    {"name": "Conductivity","port": "/dev/ttyUSB1", "baudrate": 115200},
    {"name": "Magnetic",    "port": "/dev/ttyUSB2", "baudrate": 19200},
    {"name": "XRF",         "port": "/dev/ttyUSB3", "baudrate": 19200},
    {"name": "AI Vision",   "port": "/dev/ttyUSB4", "baudrate": 115200},
]

DEVICE_ICONS = {
    "Weighing":     "https://img.icons8.com/?size=100&id=109650&format=png&color=000000",
    "Conductivity": "https://img.icons8.com/?size=100&id=asg3iKsBbXH7&format=png&color=000000",
    "Magnetic":     "https://img.icons8.com/?size=100&id=31414&format=png&color=000000",
    "XRF":          "https://img.icons8.com/?size=100&id=QVWfcpeusQau&format=png&color=000000",
    "AI Vision":    "https://img.icons8.com/?size=100&id=5g55QDdzH1wG&format=png&color=000000",
}

OTHER_ICONS = {
    "loading": "https://img.icons8.com/?size=100&id=116478&format=png&color=000000"
}

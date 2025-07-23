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
    "Weighing":     "images/weighing.png",
    "Conductivity": "images/conductivity.png",
    "Magnetic":     "images/magnetic.png",
    "XRF":          "images/xrf.png",
    "AI Vision":    "images/aivision.png",
}

OTHER_ICONS = {
    "loading": "images/loading.png",
    "place_holder": "images/placeholder.png",
    "maincontroller": "images/maincontroller.png",
}

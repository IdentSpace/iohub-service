import sys
import os
import time
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.driver.feig_cpr0210 import CPR0210

lock = CPR0210({"port": "COM9", "baudrate": 38400, "timeout": 0.3})

while lock.serial is None or not lock.serial.is_open:
    print("Waiting for HAW-2GLOCK to connect...")
    lock.connect()
    time.sleep(1)

# lock.listen()
lock.buzzer_on()
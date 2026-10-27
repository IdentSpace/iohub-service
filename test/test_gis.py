import sys
import os
import time
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.driver.gis_tshr import GiSTSHR
import logging

logger = logging.getLogger("uvicorn.error")
logging.basicConfig(level=logging.DEBUG, handlers=[logging.StreamHandler()])


reader = GiSTSHR(args={'port':'COM3', 'baudrate':19200})

# reader.listen()
# reader.connect()
# reader.make_red_the_default()
reader.listen_in_thread()
# reader.set_mode()
# reader.set_led_d(red=True, green=True)
# reader.set_led_low_level(0xC0, 0x40)
# reader.control_leds(red=True, green=True, yellow=False, buzzer=False)
# reader.set_led_direct(red=True)
# reader.ping()

while(True):
	pass
# reader.serial.write()

import sys
import os
import time
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.driver.feig_cpr46 import CPR46
import logging

logger = logging.getLogger("uvicorn.error")
logging.basicConfig(level=logging.DEBUG, handlers=[logging.StreamHandler()])

reader = CPR46({"port": "COM9", "baudrate": 38400, "timeout": 0.2})


reader.listen()
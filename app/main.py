from pathlib import Path
import os
import sys

# Make `python app/main.py` work by adding the repository root before imports
# that use the `app.*` package.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
	sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")

from app.api.application import create_api
import tomllib
from app.db.session import initialize_database
from app.core.utils import get_resource_path
from app.core.threadrunner import start_threading
from app.core.scheduler import start_scheduler
from contextlib import asynccontextmanager
import logging
from app.core.logger import configure_logging

log_path = configure_logging()
logger = logging.getLogger(__name__)
logger.info("Writing application logs to %s", log_path.resolve())
initialize_database()

@asynccontextmanager
async def lifespan(app: FastAPI):
	from app.core.webhook_dispatcher import start_webhook_worker, stop_webhook_worker
	from app.core.threadrunner import stop_threading
	from app.core.scheduler import stop_scheduler
	start_webhook_worker()
	start_scheduler()
	await start_threading()
	try:
		yield
	finally:
		stop_threading()
		stop_scheduler()
		stop_webhook_worker()

app = create_api(lifespan=lifespan)


TOML_PATH = get_resource_path("pyproject.toml")
with open(TOML_PATH, "rb") as f:
	config = tomllib.load(f)

# TODO: Output system information here
logger.info("%s %s is running", config["project"]["name"], config["project"]["version"])


if __name__ == "__main__":
	import uvicorn
	uvicorn.run(
		app,
		host=os.getenv("APP_HOST", "0.0.0.0"),
		port=int(os.getenv("APP_PORT", "8000")),
	)

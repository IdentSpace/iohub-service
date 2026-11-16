"""API construction shared by the service and offline OpenAPI export."""
from fastapi import FastAPI

from app.api import auth_routes, config_routes, device_routes
from app.api.v2.devices import router as devices_v2_router


def create_api(*, lifespan=None) -> FastAPI:
    app = FastAPI(lifespan=lifespan)
    app.include_router(devices_v2_router, prefix="/api/v2")
    app.include_router(config_routes.router, prefix="/api/config", tags=["Config"])
    app.include_router(device_routes.router, prefix="/api/device", tags=["Devices"])
    app.include_router(auth_routes.router, prefix="/auth", tags=["Auth"])

    @app.get("/")
    def read_root():
        return {"message": "Welcome to IOHub Service!"}

    @app.get("/health")
    def read_healt():
        return {"message": "fine"}

    return app

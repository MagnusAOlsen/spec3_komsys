import os
import logging

from fastapi.encoders import jsonable_encoder
from fastapi.staticfiles import StaticFiles
from logic import weather
from fastapi.responses import FileResponse, JSONResponse
from contextlib import asynccontextmanager
from fastapi.middleware.cors import CORSMiddleware
from service import single_ride_service, multi_ride_service
from fastapi import FastAPI, Response, Request, Query, APIRouter

DEPLOYMENT_MODE = os.getenv('DEPLOYMENT_MODE', 'TEST')
DISABLE_MQTT    = os.getenv("DISABLE_MQTT", "False").lower() == "true"

TEST_COORDINATES = (63.41947, 10.40174)

logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    set_single_ride_service()
    set_multi_ride_service()

    logger.info("Initializing single ride service")
    logger.info("Initializing multi ride service")
    
    yield

    app.state.db_client.delete_inactive_rentals()
    # app.state.db_client.close()
    app.state.mqtt_client.stop()

    logger.error("Stopping DB client")
    logger.error("Stopping MQTT client")
    logger.error("Stopping FastAPI app")



app = FastAPI(lifespan=lifespan)
api_router = APIRouter()



app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=True,
)


frontend_path = "/frontend/app/dist"
index_file = os.path.join(frontend_path, "index.html")

app.mount("/static", StaticFiles(directory=frontend_path), name="static")

app.mount("/assets", StaticFiles(directory=os.path.join(frontend_path, "assets")), name="assets")







def get_app():
    """
    Returns the FastAPI app instance.
    This function is used to get the app instance in other modules.
    """
    return app



def set_mqtt_client(mqtt_client : object) -> None:
    """
    Set the MQTT client for the app.
    The MQTT client is stored in the app-state.
    """
    app.state.mqtt_client = mqtt_client



def set_db_client(db_client : object) -> None:
    """
    Set the db client for the app.
    The db client is stored in the app-state.
    """
    app.state.db_client = db_client



def set_single_ride_service() -> None:
    """
    Set the single ride service for the app.
    The single ride service is stored in the app-state.
    """
    app.state.single_ride_service = single_ride_service.single_ride_service()



def set_multi_ride_service() -> None:
    """
    Set the multi ride service for the app.
    The multi ride service is stored in the app-state.
    """
    app.state.multi_ride_service = multi_ride_service.multi_ride_service()


frontend_path = "/frontend/app/dist"
index_file = os.path.join(frontend_path, "index.html")



@api_router.get("/")
async def root():
    """
    Root endpoint for the API.
    Returns:
        dict: A dictionary containing a message: <code>"Hello from backend!"</code>.
    """
    logger.debug("Request: HTTP GET /")
    return {"message": "Hello from backend!"}


if DEPLOYMENT_MODE == "TEST":
    @app.get("/robots.txt", include_in_schema=False)
    def robots_txt():
        """
        Robots.txt endpoint for the API.
        Creates a robots.txt file for the API, making it easier to see what endpoints are available.
        This is useful for debugging and development purposes.
        The robots.txt file is not intended for production use. Will return HTTP 401 Forbidden 
        if app is deployed in prod.

        Returns:
            Response:
            ``` 
            DEVELOPMENT_MODE == 'TEST' 
            curl -X GET http://localhost:8000/robots.txt -> 200 # OK: Returns robots.txt content.
            
            DEVELOPMENT_MODE == 'PROD'
            curl -X GET http://localhost:8000/robots.txt -> 401 # Forbidden: Returns nothing.
            ```
        """
        if DEPLOYMENT_MODE == 'PROD':
            return Response(status_code=401)

        lines = [
            "User-agent: *",
        ]

        exclude_paths = ["/robots.txt", "/openapi.json", "/docs", "/redoc", "/docs/oauth2-redirect"]

        for route in app.routes:
            if hasattr(route, "path") and route.path not in exclude_paths:
                lines.append(f"Endpoint: {route.path}")

        for route in api_router.routes:
            if hasattr(route, "path"):
                full_path = f"/api/v1{route.path}"
                if full_path not in exclude_paths:
                    lines.append(f"Endpoint: {full_path}")

        return Response("\n".join(lines), media_type="text/plain")



@api_router.post("/scooter/{uuid}/single-unlock")
async def scooter_unlock_single(
    uuid: str, 
    request: Request,
    user_id: str = Query(..., description="ID of the user trying to unlock the scooter")
):
    """
    Unlock a scooter with the given UUID.
    This endpoint is used to unlock a scooter for a single user.
    Args:
        uuid (str): UUID of the scooter to unlock.
        request (Request): FastAPI request object.
        user_id (str): ID of the user trying to unlock the scooter. (Query parameter)
    Returns:
        dict: A dictionary containing a message indicating the result of the unlock operation.

    Example:
        ```
        curl -X POST http://localhost:8000/scooter/1234/single-unlock -> "unlock successful"
        curl -X POST http://localhost:8000/scooter/1235/single-unlock -> "battery too low"
        ```
    """
    logger.debug("Request: HTTP POST /scooter/{uuid}/single-unlock?user_id={user_id}")
    resp = request.app.state.single_ride_service.unlock_scooter(uuid, user_id)
    status_code = 200 if resp[0] else 400

    return JSONResponse(
        status_code=status_code,
        content=jsonable_encoder({
            "message": resp[1],
            "redirect": resp[3]
        })
    )



@api_router.post("/scooter/{uuid}/single-lock")
async def scooter_lock_single(
    uuid: str, 
    request: Request,
    user_id: str = Query(..., description="ID of the user trying to unlock the scooter")
):
    """
    Lock a scooter with the given UUID.
    This endpoint is used to lock a scooter for a single user.
    Args:
        uuid (str): UUID of the scooter to lock.
        request (Request): FastAPI request object.
        user_id (str): ID of the user trying to unlock the scooter. (Query parameter)
    Returns:
        dict: A dictionary containing a message indicating the result of the lock operation.
    Example:
        ```
        curl -X POST http://localhost:8000/scooter/1234/single-lock -> "lock successful"
        curl -X POST http://localhost:8000/scooter/1235/single-lock -> "invalid parking location"
        ```
    """
    logger.debug("Request: HTTP POST /scooter/{uuid}/single-lock?user_id={user_id}")
    resp = request.app.state.single_ride_service.lock_scooter(uuid, user_id)
    status_code = 200 if resp[0] else 400

    rental = resp[2]

    logger.debug(f"Start_time: {rental['start_time']}")

    logger.debug(f"Start_time: {rental['start_time']}")

    return JSONResponse(
        status_code=status_code,
        content=jsonable_encoder({
            "message": rental,
            "redirect": resp[3]
        })
    )



@api_router.get("/test-weather")
async def test_weather():
    """
    This endpoint is used to test the weather API.
    Returns:
        dict: A dictionary containing a message indicating the result of the weather API test.
    Example:
        ```
        curl -X GET http://localhost:8000/test-weather -> 
            "acceptable conditions <br/> temperature: 11.0 <br/> humidity: 72.4"

        curl -X GET http://localhost:8000/test-weather ->  
            "insufficient conditions <br/> temperature: -2.5 <br/> humidity: 38.1"
        ```
    """
    resp = weather.is_weather_ok(TEST_COORDINATES[0], TEST_COORDINATES[1])
    return {"message": resp[1]}



@api_router.get("/scooter/{uuid}")
async def get_scooter_info(
    uuid: str, 
    request: Request,
):
    logger.debug("Request: HTTP GET /scooter/{uuid}")
    logger.debug(f"single_ride_service: {hasattr(request.app.state, 'single_ride_service')}")
    resp = request.app.state.single_ride_service.get_scooter_info(uuid)
    return {"message": resp}


@api_router.get("/user/{id}")
async def get_user_info(
    id: str, 
    request: Request,
):
    logger.debug("Request: HTTP GET /user/{id}")
    resp = request.app.state.single_ride_service.get_user_info(id)
    return {"message": resp}


@api_router.get("/rental/{rental_id}")
async def get_rental_info(
    rental_id: str, 
    request: Request,
):
    logger.debug("Request: HTTP GET /rental/{rental_id}")
    resp = request.app.state.single_ride_service.get_rental_info(rental_id)
    return {"message": resp}


app.include_router(api_router, prefix="/api/v1")

@app.get("/{full_path:path}")
async def serve_react_app(full_path: str, request: Request):
    if full_path.startswith("api/"):
        return Response(status_code=404)

    if os.path.exists(index_file):
        return FileResponse(index_file)
    return {"error": "Frontend not built"}



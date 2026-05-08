import asyncio
import os
from typing import Optional
from datetime import datetime
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, HTTPException, Depends, Request, Response
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from google.auth.transport.requests import Request as GoogleRequest
from google.oauth2 import id_token
from itsdangerous import URLSafeTimedSerializer
from dotenv import load_dotenv
import jinja2

from irishrail import get_all_stations, get_current_trains, get_train_movements

load_dotenv()

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
SESSION_SECRET = os.getenv("SESSION_SECRET", "dev-secret-change-in-prod")
GOOGLE_MAPS_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY")

if not GOOGLE_CLIENT_ID or not GOOGLE_MAPS_API_KEY:
    raise RuntimeError("GOOGLE_CLIENT_ID and GOOGLE_MAPS_API_KEY env vars required")

serializer = URLSafeTimedSerializer(SESSION_SECRET)
SESSION_COOKIE_NAME = "session"
SESSION_COOKIE_MAX_AGE = 7 * 24 * 60 * 60


class WSConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, data: dict):
        disconnected = []
        for conn in self.active_connections:
            try:
                await conn.send_json(data)
            except Exception:
                disconnected.append(conn)
        for conn in disconnected:
            self.disconnect(conn)


manager = WSConnectionManager()
stations_cache: list[dict] = []
trains_cache: dict[str, dict] = {}


async def load_stations():
    global stations_cache
    try:
        stations_cache = await get_all_stations()
    except Exception as e:
        print(f"Failed to load stations: {e}")


async def poll_trains():
    global trains_cache
    while True:
        try:
            trains = await get_current_trains()
            trains_cache = {t["code"]: t for t in trains}
            await manager.broadcast({
                "type": "trains_update",
                "trains": trains
            })
        except Exception as e:
            print(f"Failed to poll trains: {e}")
        await asyncio.sleep(15)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # startup
    await load_stations()
    poll_task = asyncio.create_task(poll_trains())
    yield
    # shutdown
    poll_task.cancel()


app = FastAPI(lifespan=lifespan)

# Mount static files
try:
    app.mount("/static", StaticFiles(directory="../frontend"), name="static")
except:
    pass


class GoogleTokenRequest(BaseModel):
    token: str


def get_session_user(request: Request) -> Optional[dict]:
    """Extract and validate session cookie."""
    session_cookie = request.cookies.get(SESSION_COOKIE_NAME)
    if not session_cookie:
        return None
    try:
        user = serializer.loads(session_cookie, max_age=SESSION_COOKIE_MAX_AGE)
        return user
    except Exception:
        return None


async def require_auth(request: Request) -> dict:
    user = get_session_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Unauthorized")
    return user


@app.get("/auth/me")
async def get_user(user: dict = Depends(require_auth)):
    return user


@app.post("/auth/google")
async def google_auth(req: GoogleTokenRequest, response: Response):
    try:
        google_request = GoogleRequest()
        info = id_token.verify_oauth2_token(req.token, google_request, GOOGLE_CLIENT_ID)

        if info["aud"] != GOOGLE_CLIENT_ID:
            raise HTTPException(status_code=400, detail="Invalid token audience")

        user_data = {
            "email": info.get("email"),
            "name": info.get("name"),
            "picture": info.get("picture"),
        }

        session_token = serializer.dumps(user_data)
        response.set_cookie(
            SESSION_COOKIE_NAME,
            session_token,
            max_age=SESSION_COOKIE_MAX_AGE,
            httponly=True,
            samesite="lax"
        )
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Auth failed: {str(e)}")


@app.post("/auth/logout")
async def logout(response: Response):
    response.delete_cookie(SESSION_COOKIE_NAME)
    return {"success": True}


@app.get("/stations")
async def get_stations(user: dict = Depends(require_auth)):
    return {"stations": stations_cache}


@app.get("/train/{code}/movements")
async def get_movements(code: str, date: str, user: dict = Depends(require_auth)):
    try:
        movements = await get_train_movements(code, date)
        return {"movements": movements}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.websocket("/ws/trains")
async def websocket_trains(websocket: WebSocket, request: Request):
    user = get_session_user(request)
    if not user:
        await websocket.close(code=1008, reason="Unauthorized")
        return

    await manager.connect(websocket)
    try:
        await websocket.send_json({
            "type": "initial",
            "stations": stations_cache,
            "trains": list(trains_cache.values())
        })
        while True:
            await websocket.receive_text()
    except Exception:
        pass
    finally:
        manager.disconnect(websocket)


@app.get("/", response_class=HTMLResponse)
async def get_index(request: Request):
    """Serve index.html with Google Maps API key injected."""
    try:
        with open("../frontend/index.html", "r") as f:
            template_str = f.read()
        template = jinja2.Template(template_str)
        html = template.render(google_maps_api_key=GOOGLE_MAPS_API_KEY)
        return html
    except FileNotFoundError:
        return "<h1>Frontend files not found</h1>"


@app.get("/login", response_class=HTMLResponse)
async def get_login(request: Request):
    """Serve login.html with Google Client ID injected."""
    try:
        with open("../frontend/login.html", "r") as f:
            template_str = f.read()
        template = jinja2.Template(template_str)
        html = template.render(google_client_id=GOOGLE_CLIENT_ID)
        return html
    except FileNotFoundError:
        return "<h1>Login page not found</h1>"


@app.get("/app.js")
async def get_app_js():
    try:
        return FileResponse("../frontend/app.js", media_type="application/javascript")
    except FileNotFoundError:
        return {"error": "app.js not found"}


@app.get("/style.css")
async def get_style_css():
    try:
        return FileResponse("../frontend/style.css", media_type="text/css")
    except FileNotFoundError:
        return {"error": "style.css not found"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

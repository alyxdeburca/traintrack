import asyncio
import os
from typing import Optional
from datetime import datetime
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, HTMLResponse
from pydantic import BaseModel
from dotenv import load_dotenv

from irishrail import get_all_stations, get_current_trains, get_train_movements

load_dotenv()



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




@app.get("/stations")
async def get_stations():
    return {"stations": stations_cache}


@app.get("/train/{code}/movements")
async def get_movements(code: str, date: str):
    try:
        movements = await get_train_movements(code, date)
        return {"movements": movements}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.websocket("/ws/trains")
async def websocket_trains(websocket: WebSocket):
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
    """Serve index.html."""
    try:
        with open("../frontend/index.html", "r") as f:
            return f.read()
    except FileNotFoundError:
        return "<h1>Frontend files not found</h1>"


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

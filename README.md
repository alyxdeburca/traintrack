# TrainTrack 🚂

A real-time web app displaying Irish Rail trains on OpenStreetMap, with live position updates via WebSocket. Fully public and anonymous — no authentication required!

## Features

- **Live train tracking** on OpenStreetMap with real-time position updates
- **Station markers** showing all Irish Rail stations
- **Train sidebar** listing all currently running trains
- **Direction-coded colors** (Northbound, Southbound, etc.)
- **Responsive design** for desktop and mobile
- **Zero authentication** — fully open and accessible to everyone
- **No API keys needed** — uses free OpenStreetMap tiles and Irish Rail API

## Setup

### Prerequisites

- Python 3.10+

### 1. Install Dependencies

```bash
cd backend
pip install -r requirements.txt
```

### 2. Run the Server

```bash
cd backend
python -m uvicorn main:app --reload
```

The app will be available at `http://localhost` (port 80)

**Note:** Port 80 requires elevated privileges. Run with `sudo` or use a reverse proxy for production.

## How It Works

### Architecture

```
Browser (HTML/JS + Leaflet/OpenStreetMap)
    ↕ WebSocket (/ws/trains)
FastAPI Backend
    ↕ HTTP polling (every 15s)
api.irishrail.ie
```

### Components

**Frontend:**
- `index.html` — Main map view (Leaflet + OpenStreetMap) with sidebar
- `app.js` — Leaflet map initialization, WebSocket management, marker updates
- `style.css` — Responsive styling

**Backend:**
- `main.py` — FastAPI app with:
  - WebSocket hub for live train updates
  - REST endpoints for stations and train movements
  - Public access (no authentication)
- `irishrail.py` — Irish Rail API client with XML parsing

### Data Flow

1. **User opens** the app (no login required)
2. **Frontend connects** to `/ws/trains` WebSocket
3. **Backend sends initial state**: all stations + current trains
4. **Backend polls** `getCurrentTrainsXML` every 15 seconds
5. **Updates broadcast** to all connected clients
6. **Frontend updates** train markers on the map in real-time

## API Endpoints

- `GET /` — Main app (public, no auth required)
- `GET /stations` — Get all station data
- `GET /train/{code}/movements?date=YYYY-MM-DD` — Get train schedule for a specific train
- `WebSocket /ws/trains` — Live train updates

## Troubleshooting

**WebSocket connection fails:**
- Check browser console for connection errors
- Ensure backend is running and accessible at `localhost` (port 80)

**No trains visible:**
- The Irish Rail API may not have trains running (late night/early morning)
- Check the backend logs for Irish Rail API errors

## License

MIT

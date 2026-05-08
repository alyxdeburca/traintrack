# TrainTrack 🚂

A real-time web app displaying Irish Rail trains on OpenStreetMap, with live position updates via WebSocket.

## Features

- **Live train tracking** on OpenStreetMap with real-time position updates
- **Google Sign-In** authentication
- **Station markers** showing all Irish Rail stations
- **Train sidebar** listing all currently running trains
- **Direction-coded colors** (Northbound, Southbound, etc.)
- **Responsive design** for desktop and mobile
- **No API keys needed** for the map (uses free OpenStreetMap tiles)

## Setup

### Prerequisites

- Python 3.10+
- A Google Cloud project with OAuth 2.0 credentials

### 1. Create Google OAuth 2.0 Credentials

1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Create a new project or select an existing one
3. Create OAuth 2.0 credentials:
   - Go to **APIs & Services** → **Credentials**
   - Click "Create Credentials" → "OAuth client ID"
   - Application type: **Web Application**
   - Add Authorized redirect URI: `http://localhost:8000`
   - Save the **Client ID**

### 2. Install Dependencies

```bash
cd backend
pip install -r requirements.txt
```

### 3. Configure Environment

Copy `.env.example` to `.env` and fill in your credentials:

```bash
cp .env.example .env
```

Edit `.env`:
```
GOOGLE_CLIENT_ID=your_oauth_client_id
SESSION_SECRET=your_random_secret
```

### 4. Run the Server

```bash
cd backend
python -m uvicorn main:app --reload
```

The app will be available at `http://localhost:8000`

## How It Works

### Architecture

```
Browser (HTML/JS + Google Maps)
    ↕ WebSocket (/ws/trains)
FastAPI Backend
    ↕ HTTP polling (every 15s)
api.irishrail.ie
```

### Components

**Frontend:**
- `login.html` — Google Sign-In page
- `index.html` — Main map view (Leaflet + OpenStreetMap) with sidebar
- `app.js` — Leaflet map initialization, WebSocket management, marker updates
- `style.css` — Responsive styling

**Backend:**
- `main.py` — FastAPI app with:
  - Google OAuth authentication
  - WebSocket hub for live train updates
  - REST endpoints for stations and train movements
- `irishrail.py` — Irish Rail API client with XML parsing

### Data Flow

1. **User logs in** via Google Sign-In
2. **Frontend connects** to `/ws/trains` WebSocket
3. **Backend sends initial state**: all stations + current trains
4. **Backend polls** `getCurrentTrainsXML` every 15 seconds
5. **Updates broadcast** to all connected clients
6. **Frontend updates** train markers on the map in real-time

## API Endpoints

- `GET /login` — Login page
- `GET /` — Main app (requires authentication)
- `POST /auth/google` — Google OAuth callback (client sends ID token)
- `GET /auth/me` — Get current user info
- `POST /auth/logout` — Logout
- `GET /stations` — Get all station data
- `GET /train/{code}/movements?date=YYYY-MM-DD` — Get train schedule for a specific train
- `WebSocket /ws/trains` — Live train updates

## Troubleshooting

**"Invalid token audience" error:**
- Ensure `GOOGLE_CLIENT_ID` in `.env` matches the one from Google Cloud Console

**WebSocket connection fails:**
- Check browser console for CORS or connection errors
- Ensure backend is running and accessible

**No trains visible:**
- The Irish Rail API may not have trains running (late night/early morning)
- Check the backend logs for API errors

## License

MIT

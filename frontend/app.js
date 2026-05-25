let map;
let ws;
let trainMarkers = {};
let stationMarkers = {};
let stations = [];
let trains = {};

const IRELAND_CENTER = [53.35, -7.9];

// Direction to color mapping
const directionColors = {
    "Northbound": "#FF6B6B",
    "Southbound": "#4ECDC4",
    "Eastbound": "#45B7D1",
    "Westbound": "#FFA07A",
    "Dublin": "#9B59B6",
    "Cork": "#E74C3C",
    "Galway": "#3498DB",
    "Limerick": "#F39C12",
};

function getColorForDirection(direction) {
    return directionColors[direction] || "#2C3E50";
}

function getTrainMarkerIcon(direction) {
    const color = getColorForDirection(direction);
    return L.divIcon({
        html: `<div style="background-color: ${color}; width: 16px; height: 16px; border-radius: 50%; border: 2px solid white; box-shadow: 0 0 4px rgba(0,0,0,0.3);"></div>`,
        iconSize: [16, 16],
        className: 'train-marker'
    });
}

async function initMap() {
    map = L.map('map').setView(IRELAND_CENTER, 7);

    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '&copy; <a href="https://www.openstreetmap.org/">OpenStreetMap</a> contributors',
        maxZoom: 19
    }).addTo(map);

    // Load stations from API
    try {
        const resp = await fetch("/stations");
        const data = await resp.json();
        stations = data.stations || [];
        renderStationMarkers();
    } catch (err) {
        console.error("Failed to load stations:", err);
    }

    // Connect WebSocket
    connectWebSocket();
}

function renderStationMarkers() {
    stations.forEach(station => {
        const marker = L.circleMarker([station.lat, station.lng], {
            radius: 5,
            fillColor: "#95A5A6",
            color: "#fff",
            weight: 1,
            opacity: 1,
            fillOpacity: 0.6
        }).bindTooltip(station.desc, { permanent: false }).addTo(map);
        stationMarkers[station.code] = marker;
    });
}

function connectWebSocket() {
    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    ws = new WebSocket(`${protocol}//${window.location.host}/ws/trains`);

    ws.onopen = () => {
        console.log("WebSocket connected");
    };

    ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        if (data.type === "initial") {
            trains = {};
            data.trains.forEach(t => trains[t.code] = t);
            renderTrainMarkers(data.trains);
        } else if (data.type === "trains_update") {
            updateTrains(data.trains);
        }
    };

    ws.onerror = (err) => {
        console.error("WebSocket error:", err);
        // Attempt reconnect
        setTimeout(connectWebSocket, 5000);
    };

    ws.onclose = () => {
        console.log("WebSocket closed, reconnecting...");
        setTimeout(connectWebSocket, 5000);
    };
}

function renderTrainMarkers(trainList) {
    trainList.forEach(train => {
        updateTrainMarker(train);
    });
}

function updateTrains(trainList) {
    // Update existing markers and create new ones
    const newTrainCodes = new Set(trainList.map(t => t.code));
    trainList.forEach(train => {
        updateTrainMarker(train);
        trains[train.code] = train;
    });

    // Remove stale markers
    Object.keys(trainMarkers).forEach(code => {
        if (!newTrainCodes.has(code)) {
            trainMarkers[code].setMap(null);
            delete trainMarkers[code];
            delete trains[code];
        }
    });

    renderTrainsList();
}

function updateTrainMarker(train) {
    if (!train.lat || !train.lng) return;

    if (trainMarkers[train.code]) {
        trainMarkers[train.code].setLatLng([train.lat, train.lng]);
    } else {
        const marker = L.marker([train.lat, train.lng], {
            icon: getTrainMarkerIcon(train.direction)
        }).addTo(map);

        marker.on('click', (e) => {
            L.DomEvent.stop(e);
            showTrainInfo(train);
        });

        trainMarkers[train.code] = marker;
    }
}

function showTrainInfo(train) {
    const infoWindow = document.getElementById("info-window");
    const infoContent = document.getElementById("info-content");
    const direction = train.direction || "Unknown";
    const color = getColorForDirection(direction);

    infoContent.innerHTML = `
        <div style="color: ${color}; font-weight: bold; margin-bottom: 10px;">
            Train ${train.code}
        </div>
        <div><strong>Direction:</strong> ${direction}</div>
        <div><strong>Status:</strong> ${train.status || "Unknown"}</div>
        <div><strong>Message:</strong> ${(train.message || "No message").replace(/\\n/g, "<br>")}</div>
        <div style="font-size: 12px; color: #999; margin-top: 10px;">
            ${train.date || ""}
        </div>
    `;
    infoWindow.style.display = "block";
}

function renderTrainsList() {
    const list = document.getElementById("trains-list");
    const trainList = Object.values(trains).sort((a, b) => (a.code || "").localeCompare(b.code || ""));

    if (trainList.length === 0) {
        list.innerHTML = "<p class='loading-text'>No trains running</p>";
        return;
    }

    list.innerHTML = trainList.map(train => {
        const direction = train.direction || "Unknown";
        const color = getColorForDirection(direction);
        return `
            <div class="train-item" style="border-left: 4px solid ${color}">
                <strong>${train.code}</strong>
                <div style="font-size: 12px; color: #666;">
                    ${direction} • ${train.status || "Running"}
                </div>
            </div>
        `;
    }).join("");

    document.querySelectorAll(".train-item").forEach((el, idx) => {
        const train = trainList[idx];
        el.addEventListener("click", () => {
            if (trainMarkers[train.code]) {
                map.setView(trainMarkers[train.code].getLatLng(), 10);
            }
            showTrainInfo(train);
        });
    });
}

document.querySelector(".close-btn")?.addEventListener("click", () => {
    document.getElementById("info-window").style.display = "none";
});

// Close info window when clicking outside
document.addEventListener("click", (e) => {
    const infoWindow = document.getElementById("info-window");
    const isLabelOrIcon = e.target.closest(".leaflet-marker-icon") || e.target.closest(".leaflet-popup") || e.target.closest(".train-marker");
    if (!isLabelOrIcon && !infoWindow.contains(e.target) && !e.target.closest(".train-item")) {
        infoWindow.style.display = "none";
    }
});

// Initialize on DOM ready
if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initMap);
} else {
    initMap();
}

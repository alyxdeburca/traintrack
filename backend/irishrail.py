import httpx
import xml.etree.ElementTree as ET
from typing import Optional
from datetime import datetime

BASE_URL = "http://api.irishrail.ie/realtime/realtime.asmx"
NS = {"ns": "http://api.irishrail.ie/realtime/"}


async def get_all_stations() -> list[dict]:
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(f"{BASE_URL}/getAllStationsXML")
        resp.raise_for_status()
        root = ET.fromstring(resp.text)
        stations = []
        for station_elem in root.findall(".//ns:Station", NS):
            try:
                stations.append({
                    "code": station_elem.findtext("ns:StationCode", "", NS),
                    "desc": station_elem.findtext("ns:StationDesc", "", NS),
                    "id": station_elem.findtext("ns:StationId", "", NS),
                    "alias": station_elem.findtext("ns:StationAlias", "", NS),
                    "lat": float(station_elem.findtext("ns:StationLatitude", "0", NS) or "0"),
                    "lng": float(station_elem.findtext("ns:StationLongitude", "0", NS) or "0"),
                })
            except (ValueError, TypeError):
                continue
        return stations


async def get_current_trains() -> list[dict]:
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(f"{BASE_URL}/getCurrentTrainsXML")
        resp.raise_for_status()
        root = ET.fromstring(resp.text)
        trains = []
        for train_elem in root.findall(".//ns:objTrainPositions", NS):
            try:
                lat_str = train_elem.findtext("ns:TrainLatitude", "0", NS) or "0"
                lng_str = train_elem.findtext("ns:TrainLongitude", "0", NS) or "0"
                lat = float(lat_str)
                lng = float(lng_str)
                if lat == 0 or lng == 0:
                    continue
                trains.append({
                    "code": train_elem.findtext("ns:TrainCode", "", NS),
                    "status": train_elem.findtext("ns:TrainStatus", "", NS),
                    "lat": lat,
                    "lng": lng,
                    "date": train_elem.findtext("ns:TrainDate", "", NS),
                    "message": train_elem.findtext("ns:PublicMessage", "", NS),
                    "direction": train_elem.findtext("ns:Direction", "", NS),
                })
            except (ValueError, TypeError):
                continue
        return trains


async def get_train_movements(train_code: str, train_date: str) -> list[dict]:
    """Fetch detailed stop-by-stop schedule for a train."""
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(
            f"{BASE_URL}/getTrainMovementsXML",
            params={"TrainId": train_code, "TrainDate": train_date}
        )
        resp.raise_for_status()
        root = ET.fromstring(resp.text)
        movements = []
        for move_elem in root.findall(".//ns:TrainMovement", NS):
            movements.append({
                "station": move_elem.findtext("ns:StationDesc", "", NS),
                "arrival": move_elem.findtext("ns:ArrivalTime", "", NS),
                "departure": move_elem.findtext("ns:DepartureTime", "", NS),
                "status": move_elem.findtext("ns:ScheduleArrival", "", NS),
            })
        return movements

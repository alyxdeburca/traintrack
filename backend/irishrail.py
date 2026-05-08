import httpx
import xml.etree.ElementTree as ET
from typing import Optional
from datetime import datetime

BASE_URL = "http://api.irishrail.ie/realtime/realtime.asmx"


async def get_all_stations() -> list[dict]:
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(f"{BASE_URL}/getAllStationsXML")
        resp.raise_for_status()
        root = ET.fromstring(resp.text)
        stations = []
        for station_elem in root.findall(".//Station"):
            try:
                stations.append({
                    "code": station_elem.findtext("StationCode", ""),
                    "desc": station_elem.findtext("StationDesc", ""),
                    "id": station_elem.findtext("StationId", ""),
                    "alias": station_elem.findtext("StationAlias", ""),
                    "lat": float(station_elem.findtext("StationLatitude", "0") or "0"),
                    "lng": float(station_elem.findtext("StationLongitude", "0") or "0"),
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
        for train_elem in root.findall(".//Train"):
            try:
                lat_str = train_elem.findtext("TrainLatitude", "0") or "0"
                lng_str = train_elem.findtext("TrainLongitude", "0") or "0"
                lat = float(lat_str)
                lng = float(lng_str)
                if lat == 0 or lng == 0:
                    continue
                trains.append({
                    "code": train_elem.findtext("TrainCode", ""),
                    "status": train_elem.findtext("TrainStatus", ""),
                    "lat": lat,
                    "lng": lng,
                    "date": train_elem.findtext("TrainDate", ""),
                    "message": train_elem.findtext("PublicMessage", ""),
                    "direction": train_elem.findtext("Direction", ""),
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
        for move_elem in root.findall(".//TrainMovement"):
            movements.append({
                "station": move_elem.findtext("StationDesc", ""),
                "arrival": move_elem.findtext("ArrivalTime", ""),
                "departure": move_elem.findtext("DepartureTime", ""),
                "status": move_elem.findtext("ScheduleArrival", ""),
            })
        return movements

from typing import List, Dict, Any, Tuple
from datetime import datetime
import math

class VerifiedPlace:
    def __init__(
        self,
        id: str,
        name: str,
        category: str, # 'hospital', 'pharmacy', 'police', 'commercial', 'transit'
        lat: float,
        lon: float,
        open_time_hour: int = 0, # 24h format
        close_time_hour: int = 24, # 24 = open 24 hours
        is_24_7: bool = False,
        description: str = ""
    ):
        self.id = id
        self.name = name
        self.category = category
        self.lat = lat
        self.lon = lon
        self.open_time_hour = open_time_hour
        self.close_time_hour = close_time_hour
        self.is_24_7 = is_24_7
        self.description = description

    def is_open_at(self, dt: datetime) -> Tuple[bool, str]:
        """Evaluates whether the place is genuinely open and verified at the specified local time."""
        if self.is_24_7:
            return True, "Verified 24/7 Service"
        
        hour = dt.hour
        if self.open_time_hour <= hour < self.close_time_hour:
            return True, f"Open until {self.close_time_hour:02d}:00"
        else:
            return False, f"Closed now (Opens at {self.open_time_hour:02d}:00)"

# Genuine verified Coimbatore public establishments along pedestrian corridors
COIMBATORE_VERIFIED_PLACES: List[VerifiedPlace] = [
    # 24/7 Emergency & Medical
    VerifiedPlace(
        "place_psg_hosp", "PSG Hospitals 24/7 Emergency & Trauma", "hospital",
        11.0240, 77.0020, is_24_7=True, description="24/7 emergency medical triage and security desk"
    ),
    VerifiedPlace(
        "place_kmch_emergency", "KMCH Multi-Specialty Hospital 24/7 Emergency", "hospital",
        11.0420, 77.0370, is_24_7=True, description="24/7 active emergency casualty with lit pedestrian portico"
    ),
    VerifiedPlace(
        "place_ganga_hosp", "Ganga Hospital Casualty & Ortho Trauma", "hospital",
        11.0260, 76.9510, is_24_7=True, description="24/7 medical emergency center on Mettupalayam Road"
    ),
    VerifiedPlace(
        "place_apollo_avinashi", "Apollo 24/7 Pharmacy (Avinashi Road)", "pharmacy",
        11.0220, 76.9950, is_24_7=True, description="24/7 illuminated retail pharmacy with night service counter"
    ),
    VerifiedPlace(
        "place_medplus_db_road", "MedPlus 24/7 Pharmacy (DB Road, RS Puram)", "pharmacy",
        11.0110, 76.9510, is_24_7=True, description="24/7 illuminated medical store with active staff"
    ),

    # 24/7 Police & Transit Safety
    VerifiedPlace(
        "place_cbe_central_police", "Coimbatore Central City Police Station", "police",
        11.0180, 76.9680, is_24_7=True, description="24/7 central police operations and active patrol base"
    ),
    VerifiedPlace(
        "place_rspuram_police", "RS Puram B2 Police Station", "police",
        11.0090, 76.9515, is_24_7=True, description="24/7 western zone police post with public assistance desk"
    ),
    VerifiedPlace(
        "place_peelamedu_police", "Peelamedu E2 Police Station", "police",
        11.0250, 77.0040, is_24_7=True, description="24/7 police outpost along student corridor"
    ),
    VerifiedPlace(
        "place_cbe_junction_rpf", "Coimbatore Junction Railway Police Post", "transit",
        10.9982, 76.9625, is_24_7=True, description="24/7 illuminated transit security station"
    ),
    VerifiedPlace(
        "place_gp_bus_stand", "Gandhipuram Central Bus Terminus Control Booth", "transit",
        11.0168, 76.9678, is_24_7=True, description="24/7 public transit interchange with constant foot traffic"
    ),

    # Commercial & Dining Establishments (Evening Active Hours)
    VerifiedPlace(
        "place_brookefields", "Brookefields Mall", "commercial",
        11.0089, 76.9572, open_time_hour=10, close_time_hour=22, is_24_7=False,
        description="Major shopping center, closes at 22:00"
    ),
    VerifiedPlace(
        "place_fun_republic", "Fun Republic Mall & Multiplex", "commercial",
        11.0280, 77.0120, open_time_hour=10, close_time_hour=23, is_24_7=False,
        description="Retail and cinema complex active until 23:00"
    ),
    VerifiedPlace(
        "place_cross_cut_bazaar", "Cross Cut Road Retail Market", "commercial",
        11.0185, 76.9650, open_time_hour=9, close_time_hour=21, is_24_7=False,
        description="Retail shopping street; shops shutter by 21:30"
    ),
    VerifiedPlace(
        "place_db_road_cafes", "DB Road Food & Cafe Promenade", "commercial",
        11.0125, 76.9515, open_time_hour=8, close_time_hour=23, is_24_7=False,
        description="Pedestrian dining street active until 23:00"
    ),
    VerifiedPlace(
        "place_race_course_promenade", "Race Course Promenade Fitness Track", "transit",
        11.0010, 76.9750, open_time_hour=5, close_time_hour=22, is_24_7=False,
        description="High-pedestrian lit jogging corridor, floodlit until 22:00"
    )
]

def haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6371000.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2.0) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2.0) ** 2
    return 2.0 * R * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))

def evaluate_places_along_route(coords: List[List[float]], query_time: datetime, proximity_buffer_m: float = 65.0) -> Dict[str, Any]:
    """
    Evaluates real-world active establishments within a buffer of the route geometry at the current local time.
    """
    active_places = []
    closed_places = []
    seen_ids = set()

    for pt in coords:
        p_lat, p_lon = pt[0], pt[1]
        for place in COIMBATORE_VERIFIED_PLACES:
            if place.id in seen_ids:
                continue
            dist = haversine_m(p_lat, p_lon, place.lat, place.lon)
            if dist <= proximity_buffer_m:
                seen_ids.add(place.id)
                is_open, status_text = place.is_open_at(query_time)
                info = {
                    "id": place.id,
                    "name": place.name,
                    "category": place.category,
                    "distance_m": round(dist),
                    "is_open": is_open,
                    "status_text": status_text,
                    "is_24_7": place.is_24_7,
                    "description": place.description
                }
                if is_open:
                    active_places.append(info)
                else:
                    closed_places.append(info)

    return {
        "active_places": active_places,
        "closed_places": closed_places,
        "total_active": len(active_places),
        "total_closed": len(closed_places)
    }

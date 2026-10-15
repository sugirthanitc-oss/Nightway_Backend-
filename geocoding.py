import re
import math
import urllib.request
import urllib.parse
import json
from typing import List, Dict, Any, Optional, Tuple

# Curated High-Precision Coimbatore Landmarks & Neighbourhoods
COIMBATORE_LANDMARKS: List[Dict[str, Any]] = [
    # 1. Gandhipuram & Central Sector
    {
        "id": "cbe_gandhipuram_bus_stand",
        "name": "Gandhipuram Central Bus Stand (Mofussil & Town)",
        "address": "Cross Cut Road, Gandhipuram, Coimbatore 641012",
        "lat": 11.0168,
        "lon": 76.9678,
        "category": "Transit Hub",
        "neighbourhood": "Gandhipuram"
    },
    {
        "id": "cbe_brookefields_mall",
        "name": "Brookefields Mall",
        "address": "Dr Krishnasamy Mudaliyar Rd, Brookefields, Coimbatore 641001",
        "lat": 11.0089,
        "lon": 76.9572,
        "category": "Commercial & Shopping",
        "neighbourhood": "Ram Nagar"
    },
    {
        "id": "cbe_cross_cut_road",
        "name": "Cross Cut Road Commercial Promenade",
        "address": "Cross Cut Rd, Gandhipuram, Coimbatore 641012",
        "lat": 11.0185,
        "lon": 76.9650,
        "category": "Commercial Promenade",
        "neighbourhood": "Gandhipuram"
    },
    {
        "id": "cbe_100_feet_road",
        "name": "100 Feet Road (Sixth Cross Road)",
        "address": "100 Feet Rd, Gandhipuram, Coimbatore 641012",
        "lat": 11.0210,
        "lon": 76.9710,
        "category": "Arterial Road",
        "neighbourhood": "Gandhipuram"
    },

    # 2. RS Puram & West Sector
    {
        "id": "cbe_db_road_rspuram",
        "name": "Diwan Bahadur (DB) Road",
        "address": "DB Road, R.S. Puram, Coimbatore 641002",
        "lat": 11.0085,
        "lon": 76.9505,
        "category": "Commercial High Street",
        "neighbourhood": "RS Puram"
    },
    {
        "id": "cbe_cowley_brown_road",
        "name": "Cowley Brown Road",
        "address": "Cowley Brown Rd, R.S. Puram, Coimbatore 641002",
        "lat": 11.0130,
        "lon": 76.9460,
        "category": "Pedestrian Avenue",
        "neighbourhood": "RS Puram"
    },
    {
        "id": "cbe_saibaba_colony",
        "name": "Saibaba Colony (NSR Road)",
        "address": "NSR Road, Saibaba Colony, Coimbatore 641011",
        "lat": 11.0315,
        "lon": 76.9450,
        "category": "Residential & Commercial",
        "neighbourhood": "Saibaba Colony"
    },

    # 3. Town Hall, Railway Station & South Sector
    {
        "id": "cbe_railway_junction",
        "name": "Coimbatore Junction Railway Station",
        "address": "State Bank Road, Gopalapuram, Coimbatore 641018",
        "lat": 10.9980,
        "lon": 76.9620,
        "category": "Transit Hub",
        "neighbourhood": "Railway Station Area"
    },
    {
        "id": "cbe_town_hall_clock_tower",
        "name": "Town Hall (Victoria Town Hall & Clock Tower)",
        "address": "Big Bazaar St, Town Hall, Coimbatore 641001",
        "lat": 10.9940,
        "lon": 76.9605,
        "category": "Historic Landmark",
        "neighbourhood": "Town Hall"
    },
    {
        "id": "cbe_voc_park",
        "name": "V.O.C. Park & Grounds",
        "address": "Park Gate Rd, Gopalapuram, Coimbatore 641018",
        "lat": 11.0040,
        "lon": 76.9710,
        "category": "Public Promenade",
        "neighbourhood": "Gopalapuram"
    },
    {
        "id": "cbe_race_course_promenade",
        "name": "Race Course Walking Promenade",
        "address": "Race Course Rd, Gopalapuram, Coimbatore 641018",
        "lat": 11.0010,
        "lon": 76.9780,
        "category": "Lit Walking Promenade",
        "neighbourhood": "Race Course"
    },
    {
        "id": "cbe_ukkadam_bus_stand",
        "name": "Ukkadam Bus Stand & Lake Front",
        "address": "Palakkad Rd, Ukkadam, Coimbatore 641001",
        "lat": 10.9890,
        "lon": 76.9580,
        "category": "Transit Hub",
        "neighbourhood": "Ukkadam"
    },

    # 4. Peelamedu, Avinashi Road & East Sector
    {
        "id": "cbe_psg_tech_peelamedu",
        "name": "PSG College of Technology (Main Gate)",
        "address": "Avinashi Rd, Peelamedu, Coimbatore 641004",
        "lat": 11.0245,
        "lon": 77.0030,
        "category": "Educational Institution",
        "neighbourhood": "Peelamedu"
    },
    {
        "id": "cbe_fun_republic_mall",
        "name": "Fun Republic Mall",
        "address": "Avinashi Rd, Peelamedu, Coimbatore 641004",
        "lat": 11.0280,
        "lon": 77.0120,
        "category": "Shopping & Entertainment",
        "neighbourhood": "Peelamedu"
    },
    {
        "id": "cbe_nava_india",
        "name": "Nava India Signal (Avinashi Road)",
        "address": "Avinashi Rd, Peelamedu, Coimbatore 641006",
        "lat": 11.0210,
        "lon": 76.9910,
        "category": "Intersection & Transit",
        "neighbourhood": "Peelamedu"
    },
    {
        "id": "cbe_airport_sitra",
        "name": "Coimbatore International Airport (SITRA)",
        "address": "Airport Rd, Peelamedu, Coimbatore 641014",
        "lat": 11.0300,
        "lon": 77.0430,
        "category": "Airport & Transit",
        "neighbourhood": "SITRA"
    },
    {
        "id": "cbe_kmch_hospital",
        "name": "KMCH (Kovai Medical Center and Hospital)",
        "address": "Avinashi Rd, Civil Aerodrome Post, Coimbatore 641014",
        "lat": 11.0420,
        "lon": 77.0370,
        "category": "Hospital Emergency",
        "neighbourhood": "Avinashi Road"
    },

    # 5. Singanallur & Southeast Sector
    {
        "id": "cbe_singanallur_bus_stand",
        "name": "Singanallur Bus Stand",
        "address": "Trichy Rd, Singanallur, Coimbatore 641005",
        "lat": 10.9995,
        "lon": 77.0250,
        "category": "Transit Hub",
        "neighbourhood": "Singanallur"
    },
    {
        "id": "cbe_ramanathapuram_signal",
        "name": "Ramanathapuram 80 Feet Road Junction",
        "address": "Trichy Rd, Ramanathapuram, Coimbatore 641045",
        "lat": 10.9970,
        "lon": 76.9950,
        "category": "Arterial Corridor",
        "neighbourhood": "Ramanathapuram"
    },

    # 6. Saravanampatti & North Sector
    {
        "id": "cbe_saravanampatti_junction",
        "name": "Saravanampatti IT Corridor Junction",
        "address": "Sathy Rd, Saravanampatti, Coimbatore 641035",
        "lat": 11.0780,
        "lon": 76.9950,
        "category": "IT Corridor",
        "neighbourhood": "Saravanampatti"
    },
    {
        "id": "cbe_prozone_mall",
        "name": "Prozone Mall",
        "address": "Sathy Rd, Sivanandhapuram, Coimbatore 641035",
        "lat": 11.0540,
        "lon": 76.9920,
        "category": "Shopping Mall",
        "neighbourhood": "Saravanampatti"
    },

    # 7. KPRIET Campus & Arasur
    {
        "id": "cbe_kpriet_library",
        "name": "KPRIET Central Library & Academic Hub",
        "address": "KPRIET Campus, Avinashi Rd, Arasur, Coimbatore 641407",
        "lat": 11.084274,
        "lon": 77.136005,
        "category": "Academic Hub",
        "neighbourhood": "KPRIET Campus"
    },
    {
        "id": "cbe_kpriet_hostels",
        "name": "KPRIET Student Hostels Complex",
        "address": "KPRIET Campus, Arasur, Coimbatore 641407",
        "lat": 11.086305,
        "lon": 77.138145,
        "category": "Residential",
        "neighbourhood": "KPRIET Campus"
    },
    {
        "id": "cbe_kpriet_main_gate",
        "name": "KPRIET Campus Main Entrance (South Gate)",
        "address": "Campus Boulevard, Arasur, Coimbatore 641407",
        "lat": 11.076950,
        "lon": 77.140550,
        "category": "Campus Entrance",
        "neighbourhood": "Arasur"
    },
    {
        "id": "cbe_arasur_bus_stop",
        "name": "Arasur 4-Roads Bus Stop (NH 544)",
        "address": "Salem-Kochi Highway, Arasur, Coimbatore 641407",
        "lat": 11.071200,
        "lon": 77.135000,
        "category": "Transit Stop",
        "neighbourhood": "Arasur"
    }
]

# Simple in-memory LRU cache
_GEOCODE_CACHE: Dict[str, List[Dict[str, Any]]] = {}

def search_coimbatore_locations(query: str, limit: int = 6) -> List[Dict[str, Any]]:
    """
    Fast, debounced search across Coimbatore landmarks with fallback to Nominatim.
    """
    clean_q = query.strip().lower()
    if len(clean_q) < 2:
        return COIMBATORE_LANDMARKS[:limit]

    if clean_q in _GEOCODE_CACHE:
        return _GEOCODE_CACHE[clean_q]

    results = []

    # 1. Match against curated Coimbatore landmarks
    words = clean_q.split()
    for loc in COIMBATORE_LANDMARKS:
        searchable_text = f"{loc['name']} {loc['address']} {loc['neighbourhood']} {loc['category']}".lower()
        score = 0
        for word in words:
            if word in searchable_text:
                score += 1
        if score > 0:
            results.append((score, loc))

    results.sort(key=lambda x: x[0], reverse=True)
    matched = [r[1] for r in results[:limit]]

    # 2. If fewer than 2 results and query is specific, try OpenStreetMap Nominatim with Coimbatore bias
    if len(matched) < 2 and len(clean_q) >= 3:
        try:
            full_query = f"{query}, Coimbatore, Tamil Nadu, India"
            encoded_q = urllib.parse.quote(full_query)
            url = f"https://nominatim.openstreetmap.org/search?q={encoded_q}&format=json&addressdetails=1&limit={limit}&viewbox=76.88,11.10,77.16,10.95&bounded=0"
            req = urllib.request.Request(
                url,
                headers={"User-Agent": "Nightway-Coimbatore-Pedestrian-Safety/2.0"}
            )
            with urllib.request.urlopen(req, timeout=2.0) as resp:
                data = json.loads(resp.read().decode('utf-8'))
                for item in data:
                    lat = float(item.get('lat', 0.0))
                    lon = float(item.get('lon', 0.0))
                    # Check within Greater Coimbatore bounding box
                    if 10.90 <= lat <= 11.15 and 76.80 <= lon <= 77.20:
                        disp_name = item.get('display_name', '')
                        name_part = disp_name.split(',')[0]
                        matched.append({
                            "id": f"osm_{item.get('osm_id', 'loc')}",
                            "name": name_part,
                            "address": disp_name,
                            "lat": lat,
                            "lon": lon,
                            "category": item.get('type', 'Location').title(),
                            "neighbourhood": "Coimbatore"
                        })
        except Exception:
            # Graceful fallback on network timeout/offline
            pass

    # Ensure uniqueness
    seen_ids = set()
    final_results = []
    for m in matched:
        if m['id'] not in seen_ids:
            seen_ids.add(m['id'])
            final_results.append(m)

    _GEOCODE_CACHE[clean_q] = final_results[:limit]
    return final_results[:limit]

_REVERSE_GEOCODE_CACHE: Dict[Tuple[float, float], Dict[str, Any]] = {}

def haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6371000.0
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)
    a = math.sin(delta_phi / 2.0)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0)**2
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return R * c

def reverse_geocode_coordinates(lat: float, lon: float) -> Dict[str, Any]:
    """
    Reverse geocodes real GPS coordinates to a human-readable street or landmark address.
    1. Checks nearby Coimbatore landmarks (< 300m).
    2. Falls back to OpenStreetMap Nominatim reverse geocode.
    3. Graceful fallback to nearest landmark or formatted coordinate string.
    """
    cache_key = (round(lat, 4), round(lon, 4))
    if cache_key in _REVERSE_GEOCODE_CACHE:
        return _REVERSE_GEOCODE_CACHE[cache_key]

    # 1. Check if within 300m of a known Coimbatore landmark
    closest_dist = float('inf')
    closest_landmark = None
    for loc in COIMBATORE_LANDMARKS:
        d = haversine_m(lat, lon, loc['lat'], loc['lon'])
        if d < closest_dist:
            closest_dist = d
            closest_landmark = loc

    if closest_landmark and closest_dist <= 250:
        result = {
            "name": f"Near {closest_landmark['name']}",
            "address": closest_landmark['address'],
            "neighbourhood": closest_landmark.get('neighbourhood', 'Coimbatore'),
            "lat": lat,
            "lon": lon,
            "distance_to_landmark_m": round(closest_dist)
        }
        _REVERSE_GEOCODE_CACHE[cache_key] = result
        return result

    # 2. Query Nominatim Reverse Geocoding
    try:
        url = f"https://nominatim.openstreetmap.org/reverse?lat={lat}&lon={lon}&format=json&addressdetails=1"
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "Nightway-Coimbatore-Pedestrian-Safety/2.0"}
        )
        with urllib.request.urlopen(req, timeout=2.5) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            addr = data.get('address', {})
            road = addr.get('road') or addr.get('pedestrian') or addr.get('street') or addr.get('suburb') or addr.get('neighbourhood')
            suburb = addr.get('suburb') or addr.get('city_district') or addr.get('neighbourhood') or "Coimbatore"
            disp_name = data.get('display_name', '')
            
            name = road if road else disp_name.split(',')[0]
            result = {
                "name": name,
                "address": disp_name,
                "neighbourhood": suburb,
                "lat": lat,
                "lon": lon
            }
            _REVERSE_GEOCODE_CACHE[cache_key] = result
            return result
    except Exception:
        pass

    # 3. Fallback to closest known landmark or coordinate string
    if closest_landmark and closest_dist < 2000:
        result = {
            "name": f"Near {closest_landmark['name']}",
            "address": f"{closest_landmark['address']} (~{round(closest_dist)}m)",
            "neighbourhood": closest_landmark.get('neighbourhood', 'Coimbatore'),
            "lat": lat,
            "lon": lon
        }
    else:
        result = {
            "name": f"GPS Position ({lat:.4f}, {lon:.4f})",
            "address": f"Latitude: {lat:.5f}, Longitude: {lon:.5f}",
            "neighbourhood": "Coimbatore",
            "lat": lat,
            "lon": lon
        }

    _REVERSE_GEOCODE_CACHE[cache_key] = result
    return result


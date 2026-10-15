import sys
from graph_manager import graph_manager
from router import TwoPassRouter

print("Initializing Graph Manager...")
graph_manager.initialize()
router = TwoPassRouter(graph_manager)

presets = [
    {
        "name": "Preset 1: Central Library to Hostels",
        "origin": [11.084274, 77.136005],
        "destination": [11.086305, 77.138145],
        "detour": 20.0
    },
    {
        "name": "Preset 2: Arasur 4-Roads Bus Stop to Main Gate",
        "origin": [11.071200, 77.135000],
        "destination": [11.076950, 77.140550],
        "detour": 15.0
    },
    {
        "name": "Preset 3: Admin Block to Canteen",
        "origin": [11.082215, 77.134167],
        "destination": [11.083342, 77.136117],
        "detour": 15.0
    }
]

for p in presets:
    print("\n" + "="*60)
    print(f"Testing: {p['name']}")
    print("="*60)
    res = router.find_route(
        origin_lat=p["origin"][0],
        origin_lon=p["origin"][1],
        dest_lat=p["destination"][0],
        dest_lon=p["destination"][1],
        detour_budget_pct=p["detour"]
    )
    print(f"Direct Route: {res.direct_route.distance_meters}m | {res.direct_route.walk_time_minutes} min | Illumination: {res.direct_route.illumination_pct}% | Risk: {res.direct_route.risk_score} | Warnings: {res.direct_route.warning_segments_count}")
    print(f"Safe Route:   {res.safe_route.distance_meters}m | {res.safe_route.walk_time_minutes} min | Illumination: {res.safe_route.illumination_pct}% | Risk: {res.safe_route.risk_score} | Warnings: {res.safe_route.warning_segments_count}")
    print(f"Detour Budget: +{res.detour_budget_pct}% | Ceiling: {res.detour_ceiling_meters}m | Actual Detour: +{res.detour_actual_pct}%")
    print(f"Direct Coords count: {len(res.direct_route.coordinates)}, Safe Coords count: {len(res.safe_route.coordinates)}")

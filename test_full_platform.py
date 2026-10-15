import urllib.request
import urllib.parse
import json

def test_platform():
    print("="*60)
    print("RUNNING LUMOSNAV CITY-WIDE FULL PLATFORM VERIFICATION")
    print("="*60)

    # 1. Health check
    res = urllib.request.urlopen("http://localhost:8000/api/health")
    health = json.loads(res.read().decode("utf-8"))
    print("\n[TEST 1] Backend Health Check:")
    print(f"  Status: {health['status']}")
    print(f"  City: {health['city']}")
    print(f"  Nodes: {health['nodes']}, Edges: {health['edges']}")
    print(f"  Verified Patrols: {health['verified_patrols_count']}, Safe Havens: {health['safe_havens_count']}, Hazards: {health['active_hazards_count']}")
    assert health['status'] == 'healthy'
    assert 'Coimbatore' in health['city']

    # 2. Geocode search across diverse Coimbatore neighbourhoods
    test_queries = ["Gandhipuram", "RS Puram", "Town Hall", "Peelamedu", "Singanallur", "Saibaba Colony"]
    print("\n[TEST 2] Geocode Search Across Coimbatore:")
    for q in test_queries:
        encoded = urllib.parse.quote(q)
        res = urllib.request.urlopen(f"http://localhost:8000/api/geocode?q={encoded}&limit=3")
        results = json.loads(res.read().decode("utf-8"))
        assert len(results) > 0, f"Expected geocode results for {q}"
        print(f"  '{q}' -> Found {len(results)} matches: '{results[0]['name']}' ({results[0]['lat']}, {results[0]['lon']})")

    # 3. Multi-Route Pedestrian Navigation Across Coimbatore
    print("\n[TEST 3] City-Wide Pedestrian Multi-Route Calculation:")
    route_payload = json.dumps({
        "origin": [11.0168, 76.9678], # Gandhipuram
        "destination": [11.0245, 77.0030], # Peelamedu (PSG Tech)
        "origin_name": "Gandhipuram Central Bus Stand",
        "destination_name": "PSG College of Technology",
        "detour_budget_pct": 15.0
    }).encode("utf-8")
    req = urllib.request.Request("http://localhost:8000/api/route", data=route_payload, headers={"Content-Type": "application/json"})
    res = urllib.request.urlopen(req)
    route_data = json.loads(res.read().decode("utf-8"))
    
    assert len(route_data["routes"]) >= 2, "Expected multiple route alternatives"
    print(f"  Origin: {route_data['origin_name']} -> Destination: {route_data['destination_name']}")
    print(f"  Returned {len(route_data['routes'])} routes:")
    
    for r in route_data["routes"]:
        print(f"\n  * Route: [{r['id']}] '{r['title']}' ({r['color']})")
        print(f"    Distance: {r['distance_meters']} m | Walk Time: {r['walk_time_minutes']} min | Lit: {r['illumination_pct']}%")
        exp = r["safety_explanation"]
        print(f"    [Q1] Walk Time: {exp['estimated_walk_time_text']}")
        print(f"    [Q2] Safety Info: {exp['safety_info_available']}")
        print(f"    [Q3] Reason: {exp['recommendation_reason']}")
        print(f"    [Q4] Last Verified: {exp['last_verified_text']} (Freshness: {exp['patrol_freshness']})")
        print(f"    Disclaimer: {exp['disclaimer']}")

    # 4. Security & Role-Based Police Authentication
    print("\n[TEST 4] Security & Role-Based Police Auth:")
    # A. Invalid credentials test
    bad_payload = json.dumps({"username": "selvam.police", "password": "WrongPassword"}).encode("utf-8")
    bad_req = urllib.request.Request("http://localhost:8000/api/auth/login", data=bad_payload, headers={"Content-Type": "application/json"})
    try:
        urllib.request.urlopen(bad_req)
        assert False, "Unauthorized login should have failed"
    except urllib.error.HTTPError as e:
        assert e.code == 401
        print("  [PASS] Correctly rejected invalid credentials with 401 Unauthorized")

    # B. Valid officer login
    auth_payload = json.dumps({"username": "selvam.police", "password": "Patrol@CBE2026"}).encode("utf-8")
    auth_req = urllib.request.Request("http://localhost:8000/api/auth/login", data=auth_payload, headers={"Content-Type": "application/json"})
    auth_res = urllib.request.urlopen(auth_req)
    auth = json.loads(auth_res.read().decode("utf-8"))
    token = auth["token"]
    assert auth["role"] == "police"
    print(f"  [PASS] Login succeeded for {auth['full_name']} (Role: {auth['role']}, Badge: {auth['badge_number']})")

    # 5. Police Patrol Recording & Observation Submission
    print("\n[TEST 5] Police Patrol Recording & Observation Submission:")
    start_req = urllib.request.Request(
        "http://localhost:8000/api/police/patrol/start",
        data=json.dumps({"notes": "Night patrol DB Road & Cowley Brown"}).encode("utf-8"),
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {token}"}
    )
    start_res = urllib.request.urlopen(start_req)
    patrol = json.loads(start_res.read().decode("utf-8"))
    pid = patrol["patrol_session_id"]
    print(f"  [PASS] Patrol session started: {pid}")

    # Submit patrol observation with visible hazard
    sub_payload = json.dumps({
        "patrol_session_id": pid,
        "location_name": "DB Road & Cowley Brown Cross Road, RS Puram",
        "route_coords": [[11.0085, 76.9505], [11.0125, 76.9515], [11.0130, 76.9460]],
        "lighting_condition": "well_lit",
        "road_condition": "normal",
        "visible_hazards": "construction",
        "notes": "Footpath paver blocks undergoing repair near intersection. Caution advised for night joggers."
    }).encode("utf-8")
    sub_req = urllib.request.Request(
        "http://localhost:8000/api/police/patrol/submit",
        data=sub_payload,
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {token}"}
    )
    sub_res = urllib.request.urlopen(sub_req)
    sub_data = json.loads(sub_res.read().decode("utf-8"))
    print(f"  [PASS] Observation submitted & verified: {sub_data['observation_id']}")
    print(f"         Expires at: {sub_data['expires_at']}")

    # 6. Verify patrol list
    patrols_req = urllib.request.Request(
        "http://localhost:8000/api/police/patrols",
        headers={"Authorization": f"Bearer {token}"}
    )
    patrols_res = urllib.request.urlopen(patrols_req)
    patrols_list = json.loads(patrols_res.read().decode("utf-8"))
    assert len(patrols_list) > 0
    print(f"  [PASS] Retrieved {len(patrols_list)} verified patrols from database (Latest: '{patrols_list[0]['location_name']}')")

    # 7. Frontend Serving check
    print("\n[TEST 7] Frontend Web UI Health:")
    f_res = urllib.request.urlopen("http://localhost:5173")
    html = f_res.read().decode("utf-8")
    assert f_res.status == 200
    assert "LumosNav" in html
    print(f"  [PASS] Frontend served successfully on http://localhost:5173 (Status: {f_res.status})")

    print("\n" + "="*60)
    print("ALL 7 CITY-WIDE VERIFICATION STAGES PASSED WITH 100% SUCCESS!")
    print("="*60)

if __name__ == "__main__":
    test_platform()

import urllib.request
import json

def run_tests():
    # 1. Health check
    res = urllib.request.urlopen('http://localhost:8000/api/health')
    health = json.loads(res.read().decode('utf-8'))
    print('Backend Health:', health)
    assert health['status'] == 'healthy'
    assert health['city'] == 'Coimbatore, Tamil Nadu, India'

    # 2. Geocode search
    res = urllib.request.urlopen('http://localhost:8000/api/geocode?q=Gandhipuram')
    geo = json.loads(res.read().decode('utf-8'))
    print('Geocode Gandhipuram results:', len(geo), geo[0]['name'])
    assert len(geo) > 0

    # 3. Multi-Route across Coimbatore (Gandhipuram to Peelamedu PSG Tech)
    route_payload = json.dumps({
        'origin': [11.0168, 76.9678],
        'destination': [11.0245, 77.0030],
        'origin_name': 'Gandhipuram Central Bus Stand',
        'destination_name': 'PSG College of Technology',
        'detour_budget_pct': 15.0
    }).encode('utf-8')
    req = urllib.request.Request('http://localhost:8000/api/route', data=route_payload, headers={'Content-Type': 'application/json'})
    res = urllib.request.urlopen(req)
    route_data = json.loads(res.read().decode('utf-8'))
    print('Calculated Routes count:', len(route_data['routes']))
    for r in route_data['routes']:
        print(f"Route [{r['id']}] {r['title']}: {r['distance_meters']}m, {r['walk_time_minutes']}min, {r['illumination_pct']}% lit")
        print('  Q1 Walk Time:', r['safety_explanation']['estimated_walk_time_text'])
        print('  Q2 Safety Info:', r['safety_explanation']['safety_info_available'])
        print('  Q3 Why:', r['safety_explanation']['recommendation_reason'])
        print('  Q4 Last Verified:', r['safety_explanation']['last_verified_text'])

    # 4. Police Auth Login
    auth_payload = json.dumps({
        'username': 'selvam.police',
        'password': 'Patrol@CBE2026'
    }).encode('utf-8')
    req = urllib.request.Request('http://localhost:8000/api/auth/login', data=auth_payload, headers={'Content-Type': 'application/json'})
    res = urllib.request.urlopen(req)
    auth = json.loads(res.read().decode('utf-8'))
    print('Police Login Success:', auth['full_name'], 'Role:', auth['role'], 'Badge:', auth['badge_number'])
    token = auth['token']
    assert auth['role'] == 'police'

    # 5. Start Patrol
    p_start_req = urllib.request.Request(
        'http://localhost:8000/api/police/patrol/start',
        data=json.dumps({'notes': 'Night sector patrol'}).encode('utf-8'),
        headers={'Content-Type': 'application/json', 'Authorization': f'Bearer {token}'}
    )
    res = urllib.request.urlopen(p_start_req)
    p_start = json.loads(res.read().decode('utf-8'))
    print('Patrol Started Session ID:', p_start['patrol_session_id'])
    pid = p_start['patrol_session_id']

    # 6. Submit Patrol
    p_submit_payload = json.dumps({
        'patrol_session_id': pid,
        'location_name': 'Avinashi Road & Nava India Junction',
        'route_coords': [[11.0180, 76.9750], [11.0210, 76.9910]],
        'lighting_condition': 'well_lit',
        'road_condition': 'normal',
        'visible_hazards': 'none',
        'notes': 'Night pedestrian patrol completed, streetlights active, no security incidents.'
    }).encode('utf-8')
    p_sub_req = urllib.request.Request(
        'http://localhost:8000/api/police/patrol/submit',
        data=p_submit_payload,
        headers={'Content-Type': 'application/json', 'Authorization': f'Bearer {token}'}
    )
    res = urllib.request.urlopen(p_sub_req)
    p_sub = json.loads(res.read().decode('utf-8'))
    print('Patrol Submitted Observation ID:', p_sub['observation_id'], p_sub['message'])

    print('\n>>> ALL BACKEND VERIFICATION CHECKS PASSED 100%! <<<')

if __name__ == '__main__':
    run_tests()

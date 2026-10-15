import os
import json
import secrets
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, status, Header, Depends, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from models import (
    RouteRequest, 
    MultiRouteResponse, 
    RouteResponse, 
    PresetRoute,
    AuthLoginRequest, 
    AuthRegisterRequest,
    LogoutRequest,
    AuthUserResponse,
    PatrolStartRequest, 
    PatrolRecordRequest, 
    PatrolSubmitRequest
)
from database import (
    get_db, 
    init_db, 
    verify_password, 
    hash_password
)
from safe_havens import COIMBATORE_SAFE_HAVENS
from geocoding import search_coimbatore_locations, reverse_geocode_coordinates
from graph_manager import graph_manager
from router import multi_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("=" * 65)
    print("Nightway 2.0 Backend Startup: Greater Coimbatore Walking Network...")
    print("=" * 65)
    init_db()
    graph_manager.initialize()
    print("Nightway 2.0 Backend Ready.")
    yield
    print("Nightway 2.0 Backend Shutdown.")

app = FastAPI(
    title="Nightway — City-Wide Nighttime Pedestrian Safety Platform",
    description="Coimbatore City-Wide Pedestrian Navigation Engine with Evidence-Based Safety Routing & Police Patrol Verification",
    version="2.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -------------------------------------------------------------
# AUTHENTICATION & SECURITY DEPENDENCIES
# -------------------------------------------------------------
def get_current_user(authorization: Optional[str] = Header(None)) -> Dict[str, Any]:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid authentication token."
        )
    token = authorization.split(" ")[1]
    conn = get_db()
    cursor = conn.cursor()
    now_str = datetime.utcnow().isoformat()
    cursor.execute("""
    SELECT u.id, u.username, u.role, u.full_name, u.badge_number, u.station, s.expires_at
    FROM sessions s
    JOIN users u ON s.user_id = u.id
    WHERE s.token = ? AND s.expires_at > ?;
    """, (token, now_str))
    user = cursor.fetchone()
    conn.close()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session expired or invalid. Please sign in again."
        )
    return dict(user)

def require_police_or_admin(user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
    if user['role'] not in ['police', 'admin']:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access restricted: Authorized police personnel only."
        )
    return user

# -------------------------------------------------------------
# 1. CORE NAVIGATION & GEOCODING ENDPOINTS
# -------------------------------------------------------------
@app.get("/api/health")
def health_check():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM observations WHERE status = 'verified';")
    active_obs_count = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM hazards WHERE is_active = 1;")
    hazards_count = cursor.fetchone()[0]
    conn.close()

    return {
        "status": "healthy",
        "city": "Coimbatore, Tamil Nadu, India",
        "nodes": len(graph_manager.G.nodes) if graph_manager.G else 0,
        "edges": len(graph_manager.G.edges) if graph_manager.G else 0,
        "safe_havens_count": len(COIMBATORE_SAFE_HAVENS),
        "verified_patrols_count": active_obs_count,
        "active_hazards_count": hazards_count
    }

@app.get("/api/geocode")
def geocode_search(q: str = Query(..., min_length=1), limit: int = 6):
    """Debounced search across Coimbatore landmarks, neighbourhoods, and streets."""
    return search_coimbatore_locations(q, limit=limit)

@app.get("/api/reverse-geocode")
def reverse_geocode(lat: float = Query(...), lon: float = Query(...)):
    """Reverse geocodes a latitude/longitude coordinate pair to a human-readable street or landmark address."""
    return reverse_geocode_coordinates(lat, lon)

@app.get("/api/safe-havens")
def get_safe_havens():
    """Returns 24/7 verified police posts, hospitals, and security booths across Coimbatore."""
    return COIMBATORE_SAFE_HAVENS

@app.get("/api/hazards")
def get_hazards():
    """Returns active road closures and temporary hazards across Coimbatore."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id, category, description, latitude, longitude, severity, reported_at, verified_by FROM hazards WHERE is_active = 1;")
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

@app.post("/api/route", response_model=MultiRouteResponse)
def calculate_pedestrian_route(req: RouteRequest):
    """
    Computes Google Maps-style multiple walking routes across Coimbatore:
    - Recommended lower-risk route (emerald green)
    - Alternative route (blue/slate)
    - Direct shortest route (contrasting red/orange)
    With explicit 4-question safety explanations.
    """
    if len(req.origin) < 2 or len(req.destination) < 2:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Origin and destination must be valid [latitude, longitude] pairs."
        )

    try:
        response = multi_router.find_multi_routes(
            origin_lat=req.origin[0],
            origin_lon=req.origin[1],
            dest_lat=req.destination[0],
            dest_lon=req.destination[1],
            origin_name=req.origin_name or "Selected Origin",
            dest_name=req.destination_name or "Selected Destination",
            detour_budget_pct=req.detour_budget_pct
        )
        return response
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

# -------------------------------------------------------------
# 2. AUTHENTICATION & ROLE-BASED ACCESS
# -------------------------------------------------------------
@app.post("/api/auth/login", response_model=AuthUserResponse)
def login(req: AuthLoginRequest):
    """Secure login with role-based session token."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
    SELECT id, username, password_hash, salt, role, full_name, badge_number, station 
    FROM users 
    WHERE username = ?;
    """, (req.username.strip().lower(),))
    user = cursor.fetchone()

    if not user or not verify_password(req.password, user['salt'], user['password_hash']):
        conn.close()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials. Please verify your username and password."
        )

    # Issue secure session token (valid for 3 days)
    token = secrets.token_urlsafe(32)
    now = datetime.utcnow()
    expires_at = (now + timedelta(days=3)).isoformat()

    cursor.execute("""
    INSERT INTO sessions (token, user_id, created_at, expires_at)
    VALUES (?, ?, ?, ?);
    """, (token, user['id'], now.isoformat(), expires_at))

    # Audit log
    cursor.execute("""
    INSERT INTO audit_logs (user_id, action, details, timestamp)
    VALUES (?, ?, ?, ?);
    """, (user['id'], "LOGIN_SUCCESS", f"User logged in with role {user['role']}", now.isoformat()))

    conn.commit()
    conn.close()

    return AuthUserResponse(
        id=user['id'],
        username=user['username'],
        role=user['role'],
        full_name=user['full_name'],
        badge_number=user['badge_number'],
        station=user['station'],
        token=token
    )

@app.get("/api/auth/me", response_model=AuthUserResponse)
def get_me(user: Dict[str, Any] = Depends(get_current_user)):
    """Returns current authenticated user details."""
    return AuthUserResponse(
        id=user['id'],
        username=user['username'],
        role=user['role'],
        full_name=user['full_name'],
        badge_number=user['badge_number'],
        station=user['station'],
        token=""
    )

@app.post("/api/auth/register", response_model=AuthUserResponse)
def register(req: AuthRegisterRequest):
    """Registers a new public pedestrian or campus user."""
    username = req.username.strip().lower()
    if not username:
        raise HTTPException(status_code=400, detail="Username is required.")
    if len(req.password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters long.")

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM users WHERE username = ?;", (username,))
    if cursor.fetchone():
        conn.close()
        raise HTTPException(status_code=400, detail="An account with this username already exists.")

    pw_hash, salt = hash_password(req.password)
    now = datetime.utcnow()
    cursor.execute("""
    INSERT INTO users (username, password_hash, salt, role, full_name, badge_number, station, created_at)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?);
    """, (username, pw_hash, salt, req.role or "public", req.full_name, None, None, now.isoformat()))
    user_id = cursor.lastrowid

    # Create active session token
    token = secrets.token_urlsafe(32)
    expires_at = (now + timedelta(days=3)).isoformat()
    cursor.execute("""
    INSERT INTO sessions (token, user_id, created_at, expires_at)
    VALUES (?, ?, ?, ?);
    """, (token, user_id, now.isoformat(), expires_at))

    cursor.execute("""
    INSERT INTO audit_logs (user_id, action, details, timestamp)
    VALUES (?, ?, ?, ?);
    """, (user_id, "REGISTER", f"User registered as {req.role or 'public'}", now.isoformat()))

    conn.commit()
    conn.close()

    return AuthUserResponse(
        id=user_id,
        username=username,
        role=req.role or "public",
        full_name=req.full_name,
        badge_number=None,
        station=None,
        token=token
    )

@app.post("/api/auth/logout")
def logout(body: Optional[LogoutRequest] = None, authorization: Optional[str] = Header(None)):
    """
    Revokes the active session token from the SQLite sessions table.
    Accepts token via Authorization Header ('Bearer <token>') or JSON body ({ 'token': '<token>' }).
    Logs security audit event and returns 200 OK.
    """
    token = None
    if authorization and authorization.startswith("Bearer "):
        token = authorization.split(" ")[1]
    elif body and body.token:
        token = body.token

    if token:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT user_id FROM sessions WHERE token = ?;", (token,))
        row = cursor.fetchone()
        user_id = row['user_id'] if row else None

        cursor.execute("DELETE FROM sessions WHERE token = ?;", (token,))
        if user_id:
            cursor.execute("""
            INSERT INTO audit_logs (user_id, action, details, timestamp)
            VALUES (?, ?, ?, ?);
            """, (user_id, "LOGOUT", "Session revoked and user logged out", datetime.utcnow().isoformat()))
        conn.commit()
        conn.close()

    return {"status": "success", "message": "Logged out successfully."}

# -------------------------------------------------------------
# 3. POLICE PATROL RECORDING & VERIFICATION PORTAL
# -------------------------------------------------------------
@app.post("/api/police/patrol/start")
def start_patrol_session(
    req: PatrolStartRequest,
    user: Dict[str, Any] = Depends(require_police_or_admin)
):
    """Starts an active patrol recording session for an authorized officer."""
    session_id = f"patrol_{secrets.token_hex(6)}"
    now = datetime.utcnow().isoformat()
    station = req.station or user.get('station') or "Coimbatore City Central Station"

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO patrol_sessions (id, officer_id, officer_name, badge_number, station, start_time, status, route_coords, created_at)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
    """, (session_id, user['id'], user['full_name'], user['badge_number'] or "POLICE", station, now, "active", json.dumps([]), now))
    
    cursor.execute("""
    INSERT INTO audit_logs (user_id, action, details, timestamp)
    VALUES (?, ?, ?, ?);
    """, (user['id'], "PATROL_START", f"Started patrol session {session_id}", now))

    conn.commit()
    conn.close()

    return {
        "status": "success",
        "patrol_session_id": session_id,
        "officer": user['full_name'],
        "start_time": now
    }

@app.post("/api/police/patrol/record")
def record_patrol_point(
    req: PatrolRecordRequest,
    user: Dict[str, Any] = Depends(require_police_or_admin)
):
    """Appends GPS coordinate point to an active patrol session."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT route_coords, status FROM patrol_sessions WHERE id = ? AND officer_id = ?;", (req.patrol_session_id, user['id']))
    row = cursor.fetchone()

    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="Patrol session not found or not owned by officer.")

    if row['status'] != 'active':
        conn.close()
        raise HTTPException(status_code=400, detail="Cannot record to an inactive or submitted patrol session.")

    coords = json.loads(row['route_coords'] or "[]")
    coords.append([req.latitude, req.longitude])

    cursor.execute("UPDATE patrol_sessions SET route_coords = ? WHERE id = ?;", (json.dumps(coords), req.patrol_session_id))
    conn.commit()
    conn.close()

    return {"status": "success", "point_count": len(coords)}

@app.post("/api/police/patrol/submit")
def submit_patrol_observation(
    req: PatrolSubmitRequest,
    user: Dict[str, Any] = Depends(require_police_or_admin)
):
    """
    Submits patrol route observations:
    - Lighting condition
    - Road condition & visible hazards
    - Officer field notes
    Immediately becomes active in safety route evaluations with 12-hour validity.
    """
    if len(req.route_coords) < 2:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Patrol submission must include at least 2 recorded GPS coordinate points."
        )

    obs_id = f"obs_{secrets.token_hex(6)}"
    now = datetime.utcnow()
    observed_at = now.isoformat()
    # 12-hour validity window for nighttime patrol observations
    expires_at = (now + timedelta(hours=12)).isoformat()

    conn = get_db()
    cursor = conn.cursor()

    # 1. Update patrol session status
    cursor.execute("""
    UPDATE patrol_sessions 
    SET end_time = ?, status = 'submitted', route_coords = ? 
    WHERE id = ?;
    """, (observed_at, json.dumps(req.route_coords), req.patrol_session_id))

    # 2. Insert verified observation
    cursor.execute("""
    INSERT INTO observations (
        id, patrol_session_id, officer_id, officer_name, badge_number, station,
        location_name, route_coords, lighting_condition, road_condition, visible_hazards,
        notes, observed_at, verified_at, expires_at, status, created_at
    )
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
    """, (
        obs_id, req.patrol_session_id, user['id'], user['full_name'], user['badge_number'] or "TN-POLICE",
        user.get('station') or "Coimbatore City Central Police", req.location_name,
        json.dumps(req.route_coords), req.lighting_condition, req.road_condition, req.visible_hazards,
        req.notes or "", observed_at, observed_at, expires_at, "verified", observed_at
    ))

    # 3. If visible hazard reported, create corresponding hazard record
    if req.visible_hazards != "none":
        h_id = f"haz_{secrets.token_hex(4)}"
        cursor.execute("""
        INSERT INTO hazards (id, category, description, latitude, longitude, severity, reported_at, verified_by, is_active)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
        """, (
            h_id, req.visible_hazards.replace('_', ' ').title(),
            f"Officer reported: {req.notes or req.visible_hazards} near {req.location_name}",
            req.route_coords[0][0], req.route_coords[0][1], "medium", observed_at, user['full_name'], 1
        ))

    # 4. Audit log
    cursor.execute("""
    INSERT INTO audit_logs (user_id, action, details, timestamp)
    VALUES (?, ?, ?, ?);
    """, (user['id'], "OBSERVATION_SUBMITTED", f"Submitted observation {obs_id} for {req.location_name}", observed_at))

    conn.commit()
    conn.close()

    # Trigger graph manager re-enrichment so routing takes this new observation into account immediately
    graph_manager._apply_database_patrols_and_hazards()
    graph_manager._compute_edge_risk_weights()

    return {
        "status": "success",
        "observation_id": obs_id,
        "location_name": req.location_name,
        "verified_at": observed_at,
        "expires_at": expires_at,
        "message": "Patrol observation successfully verified and published to Nightway city routing engine."
    }

@app.get("/api/police/patrols")
def list_patrols(user: Dict[str, Any] = Depends(require_police_or_admin)):
    """Returns recent patrol sessions and observations for the police portal dashboard."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
    SELECT o.id, o.patrol_session_id, o.officer_name, o.badge_number, o.station, o.location_name,
           o.route_coords, o.lighting_condition, o.road_condition, o.visible_hazards, o.notes,
           o.observed_at, o.expires_at, o.status
    FROM observations o
    ORDER BY o.observed_at DESC LIMIT 20;
    """)
    rows = cursor.fetchall()
    conn.close()

    result = []
    now = datetime.utcnow()
    for r in rows:
        item = dict(r)
        try:
            item['route_coords'] = json.loads(item['route_coords'])
        except Exception:
            pass
        # Calculate freshness
        try:
            exp = datetime.fromisoformat(item['expires_at'])
            item['is_expired'] = now > exp
            item['expires_in_hours'] = max(0.0, round((exp - now).total_seconds() / 3600.0, 1))
        except Exception:
            item['is_expired'] = False
        result.append(item)

    return result

@app.get("/api/police/observations")
def get_public_observations():
    """Returns verified patrol observations with freshness classification."""
    return multi_router._get_verified_patrols()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=False)

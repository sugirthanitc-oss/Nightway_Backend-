import sqlite3
import hashlib
import hmac
import secrets
import json
import os
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any

DB_PATH = os.path.join(os.path.dirname(__file__), "nightway.db")

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def hash_password(password: str, salt: Optional[str] = None) -> tuple[str, str]:
    """Secure PBKDF2-HMAC-SHA256 password hashing."""
    if not salt:
        salt = secrets.token_hex(16)
    pw_hash = hashlib.pbkdf2_hmac(
        'sha256',
        password.encode('utf-8'),
        salt.encode('utf-8'),
        100000
    ).hex()
    return pw_hash, salt

def verify_password(password: str, salt: str, expected_hash: str) -> bool:
    """Constant-time password verification."""
    computed_hash, _ = hash_password(password, salt)
    return hmac.compare_digest(computed_hash, expected_hash)

def init_db():
    """Initializes SQLite schema and seeds initial data."""
    conn = get_db()
    cursor = conn.cursor()

    # 1. Users table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        salt TEXT NOT NULL,
        role TEXT NOT NULL, -- 'public', 'police', 'admin'
        full_name TEXT NOT NULL,
        badge_number TEXT,
        station TEXT,
        created_at TEXT NOT NULL
    );
    """)

    # 2. Sessions table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS sessions (
        token TEXT PRIMARY KEY,
        user_id INTEGER NOT NULL,
        created_at TEXT NOT NULL,
        expires_at TEXT NOT NULL,
        FOREIGN KEY (user_id) REFERENCES users (id)
    );
    """)

    # 3. Patrol Sessions table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS patrol_sessions (
        id TEXT PRIMARY KEY,
        officer_id INTEGER NOT NULL,
        officer_name TEXT NOT NULL,
        badge_number TEXT NOT NULL,
        station TEXT NOT NULL,
        start_time TEXT NOT NULL,
        end_time TEXT,
        status TEXT NOT NULL, -- 'active', 'completed', 'submitted'
        route_coords TEXT, -- JSON array of [lat, lon]
        created_at TEXT NOT NULL,
        FOREIGN KEY (officer_id) REFERENCES users (id)
    );
    """)

    # 4. Route Observations table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS observations (
        id TEXT PRIMARY KEY,
        patrol_session_id TEXT NOT NULL,
        officer_id INTEGER NOT NULL,
        officer_name TEXT NOT NULL,
        badge_number TEXT NOT NULL,
        station TEXT NOT NULL,
        location_name TEXT NOT NULL,
        route_coords TEXT NOT NULL, -- JSON array of [lat, lon]
        lighting_condition TEXT NOT NULL, -- 'well_lit', 'partially_lit', 'unlit', 'unknown'
        road_condition TEXT NOT NULL, -- 'normal', 'under_construction', 'closed', 'caution'
        visible_hazards TEXT NOT NULL, -- 'none', 'poor_lighting', 'construction', 'isolated_stretch', 'stray_dogs', 'waterlogging'
        notes TEXT,
        observed_at TEXT NOT NULL,
        verified_at TEXT NOT NULL,
        expires_at TEXT NOT NULL,
        status TEXT NOT NULL, -- 'verified', 'published', 'expired', 'revoked'
        created_at TEXT NOT NULL,
        FOREIGN KEY (officer_id) REFERENCES users (id),
        FOREIGN KEY (patrol_session_id) REFERENCES patrol_sessions (id)
    );
    """)

    # 5. Road Closures and Hazards table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS hazards (
        id TEXT PRIMARY KEY,
        category TEXT NOT NULL,
        description TEXT NOT NULL,
        latitude REAL NOT NULL,
        longitude REAL NOT NULL,
        severity TEXT NOT NULL, -- 'low', 'medium', 'high'
        reported_at TEXT NOT NULL,
        verified_by TEXT NOT NULL,
        is_active INTEGER NOT NULL DEFAULT 1
    );
    """)

    # 6. Audit Logs table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS audit_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        action TEXT NOT NULL,
        details TEXT NOT NULL,
        timestamp TEXT NOT NULL
    );
    """)

    conn.commit()

    # Pre-seed users if empty
    cursor.execute("SELECT COUNT(*) FROM users;")
    if cursor.fetchone()[0] == 0:
        now_str = datetime.utcnow().isoformat()
        
        # Officer 1: Inspector Selvam
        h1, s1 = hash_password("Patrol@CBE2026")
        cursor.execute("""
        INSERT INTO users (username, password_hash, salt, role, full_name, badge_number, station, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?);
        """, ("selvam.police", h1, s1, "police", "Insp. R. Selvam", "TN-CBE-4091", "Coimbatore City Central Station (Gandhipuram)", now_str))

        # Officer 2: Sub-Inspector Priya
        h2, s2 = hash_password("Patrol@CBE2026")
        cursor.execute("""
        INSERT INTO users (username, password_hash, salt, role, full_name, badge_number, station, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?);
        """, ("priya.police", h2, s2, "police", "SI K. Priya", "TN-CBE-5823", "Traffic & Patrol Division East (Peelamedu)", now_str))

        # Administrator: Commissioner Safety Ops
        h3, s3 = hash_password("Admin@CBE2026")
        cursor.execute("""
        INSERT INTO users (username, password_hash, salt, role, full_name, badge_number, station, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?);
        """, ("admin.cbe", h3, s3, "admin", "Coimbatore City Safety Ops Admin", "CBE-HQ-01", "Coimbatore Police Commissionerate", now_str))

        # Public user: Karthik Raja
        h4, s4 = hash_password("Public@2026")
        cursor.execute("""
        INSERT INTO users (username, password_hash, salt, role, full_name, badge_number, station, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?);
        """, ("karthik.raja", h4, s4, "public", "Karthik Raja", None, None, now_str))

        conn.commit()

    # Pre-seed verified patrol observations across key Coimbatore corridors
    cursor.execute("SELECT COUNT(*) FROM observations;")
    if cursor.fetchone()[0] == 0:
        now = datetime.utcnow()
        # 1. Recent observation (2 hours ago) on Avinashi Road
        t1 = (now - timedelta(hours=2)).isoformat()
        e1 = (now + timedelta(hours=6)).isoformat()
        coords1 = [
            [11.0168, 76.9678], [11.0185, 76.9750], [11.0210, 76.9850], [11.0245, 77.0030]
        ]
        cursor.execute("""
        INSERT INTO patrol_sessions (id, officer_id, officer_name, badge_number, station, start_time, end_time, status, route_coords, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """, ("patrol_cbe_101", 1, "Insp. R. Selvam", "TN-CBE-4091", "Coimbatore City Central Station (Gandhipuram)", t1, now.isoformat(), "submitted", json.dumps(coords1), t1))

        cursor.execute("""
        INSERT INTO observations (id, patrol_session_id, officer_id, officer_name, badge_number, station, location_name, route_coords, lighting_condition, road_condition, visible_hazards, notes, observed_at, verified_at, expires_at, status, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """, ("obs_101", "patrol_cbe_101", 1, "Insp. R. Selvam", "TN-CBE-4091", "Coimbatore City Central Station (Gandhipuram)", "Avinashi Road Promenade (Gandhipuram to Peelamedu)", json.dumps(coords1), "well_lit", "normal", "none", "Pedestrian walkways active, streetlights functional at 100%, high visible surveillance.", t1, t1, e1, "verified", t1))

        # 2. Recent observation (3.5 hours ago) on DB Road & RS Puram
        t2 = (now - timedelta(hours=3, minutes=30)).isoformat()
        e2 = (now + timedelta(hours=4, minutes=30)).isoformat()
        coords2 = [
            [11.0085, 76.9505], [11.0120, 76.9520], [11.0150, 76.9490], [11.0200, 76.9470]
        ]
        cursor.execute("""
        INSERT INTO patrol_sessions (id, officer_id, officer_name, badge_number, station, start_time, end_time, status, route_coords, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """, ("patrol_cbe_102", 2, "SI K. Priya", "TN-CBE-5823", "Traffic & Patrol Division East (Peelamedu)", t2, now.isoformat(), "submitted", json.dumps(coords2), t2))

        cursor.execute("""
        INSERT INTO observations (id, patrol_session_id, officer_id, officer_name, badge_number, station, location_name, route_coords, lighting_condition, road_condition, visible_hazards, notes, observed_at, verified_at, expires_at, status, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """, ("obs_102", "patrol_cbe_102", 2, "SI K. Priya", "TN-CBE-5823", "Traffic & Patrol Division East (Peelamedu)", "DB Road & Cowley Brown Road Corridor (RS Puram)", json.dumps(coords2), "well_lit", "normal", "none", "High commercial lighting, CCTV coverage active, footpaths clear of obstruction.", t2, t2, e2, "verified", t2))

        # 3. Observation becoming outdated (16 hours ago) near Town Hall & Ukkadam
        t3 = (now - timedelta(hours=16)).isoformat()
        e3 = (now - timedelta(hours=4)).isoformat() # expired
        coords3 = [
            [10.9980, 76.9620], [10.9940, 76.9600], [10.9890, 76.9580]
        ]
        cursor.execute("""
        INSERT INTO observations (id, patrol_session_id, officer_id, officer_name, badge_number, station, location_name, route_coords, lighting_condition, road_condition, visible_hazards, notes, observed_at, verified_at, expires_at, status, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """, ("obs_103", "patrol_cbe_102", 2, "SI K. Priya", "TN-CBE-5823", "Traffic & Patrol Division East (Peelamedu)", "Oppanakara St to Ukkadam Link", json.dumps(coords3), "partially_lit", "caution", "poor_lighting", "Night market closed, streetlighting dim on secondary cross-lanes. Observation now expired.", t3, t3, e3, "expired", t3))

        conn.commit()

    # Pre-seed verified hazards if empty
    cursor.execute("SELECT COUNT(*) FROM hazards;")
    if cursor.fetchone()[0] == 0:
        now_str = datetime.utcnow().isoformat()
        cursor.execute("""
        INSERT INTO hazards (id, category, description, latitude, longitude, severity, reported_at, verified_by, is_active)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
        """, ("haz_01", "Construction", "Flyover underpass footpath maintenance with debris on 100 Feet Road", 11.0215, 76.9695, "medium", now_str, "Insp. R. Selvam", 1))

        cursor.execute("""
        INSERT INTO hazards (id, category, description, latitude, longitude, severity, reported_at, verified_by, is_active)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
        """, ("haz_02", "Unlit Shortcut", "Perimeter service shed lane behind workshop sheds unlit after 21:00", 11.0848, 77.1348, "high", now_str, "SI K. Priya", 1))

        cursor.execute("""
        INSERT INTO hazards (id, category, description, latitude, longitude, severity, reported_at, verified_by, is_active)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
        """, ("haz_03", "Temporary Closure", "Drainage construction blocking pedestrian walkway near Saibaba Colony North Link", 11.0360, 76.9420, "medium", now_str, "Insp. R. Selvam", 1))

        conn.commit()

    conn.close()

# Auto-initialize database on import
init_db()

# Nightway — Backend API & Routing Engine

Nightway is a high-performance pedestrian navigation backend engine built with FastAPI and NetworkX, designed for Coimbatore, Tamil Nadu, India. It introduces evidence-based nighttime pedestrian safety evaluation, combining OpenStreetMap streetlighting infrastructure, 24/7 safe havens, and verified police patrol records.

---

## 🚀 Key Architectural Features

1. **Two-Pass Detour-Bounded Routing**:
   - Computes physical shortest path baseline ($D_{\min}$) via Dijkstra / A*.
   - Evaluates dynamic safety penalty multipliers ($W_e = L_e \cdot M_{\text{lighting}} \cdot M_{\text{patrol}} \cdot M_{\text{hazard}}$).
   - Enforces a strict detour ceiling: $D_{\text{safe}} \le D_{\min} \cdot (1 + \frac{\text{budget}}{100})$.
2. **Sub-Millisecond Coordinate Snapping**:
   - Uses SciPy `cKDTree` spatial indexing on 50+ network junctions across greater Coimbatore.
3. **Multi-Source Evidence Synthesis**:
   - Streetlighting illumination percentage.
   - 24/7 verified police booths, hospitals, and security kiosks.
   - Time-sensitive patrol freshness evaluation (12-hour validity window).
4. **Role-Based Authentication & Verification**:
   - Secure PBKDF2-HMAC-SHA256 password hashing with unique per-user salts.
   - Session token revocation on logout (`DELETE FROM sessions WHERE token = ?`).
   - Security audit logging (`audit_logs` table).

---

## 🛠️ API Endpoints Summary

### Navigation & Geocoding
- `POST /api/route` — Computes dual pedestrian routes (Recommended Safe + Alternative/Shortest).
- `GET /api/geocode?q={query}` — Debounced search across Coimbatore landmarks and streets.
- `GET /api/reverse-geocode?lat={lat}&lon={lon}` — Converts GPS coordinates to human-readable addresses.
- `GET /api/safe-havens` — Returns verified 24/7 emergency shelters and police posts.
- `GET /api/hazards` — Active road closures and temporary nighttime hazards.
- `GET /api/health` — System status, node count, and graph metrics.

### Authentication & Sessions
- `POST /api/auth/login` — Issues 3-day secure session token.
- `POST /api/auth/register` — Citizen/student account registration.
- `POST /api/auth/logout` — Revokes session token and records audit event.
- `GET /api/auth/me` — Fetches current authenticated user profile.

### Police Patrol Verification Portal
- `POST /api/police/patrol/start` — Starts an active officer patrol tracking session.
- `POST /api/police/patrol/record` — Appends GPS coordinate waypoints to active session.
- `POST /api/police/patrol/submit` — Submits verified streetlight and road observations.
- `GET /api/police/patrols` — Retrieves verified patrol history.

---

## 💻 Local Setup & Execution

```bash
# 1. Clone repository
git clone https://github.com/sugirthanitc-oss/Nightway_Backend-.git
cd Nightway_Backend-

# 2. Create and activate virtual environment
python -m venv venv
# Windows (PowerShell):
.\venv\Scripts\Activate.ps1
# Linux / macOS:
source venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Start the server
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

Interactive API documentation will be available at:
- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`

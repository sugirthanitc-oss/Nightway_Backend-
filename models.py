from typing import List, Optional, Tuple, Dict, Any
from pydantic import BaseModel, Field
from safe_havens import SafeHaven

class RouteRequest(BaseModel):
    origin: List[float] = Field(..., description="[latitude, longitude] of origin")
    destination: List[float] = Field(..., description="[latitude, longitude] of destination")
    origin_name: Optional[str] = Field(default="Selected Origin", description="Descriptive origin name")
    destination_name: Optional[str] = Field(default="Selected Destination", description="Descriptive destination name")
    detour_budget_pct: float = Field(default=15.0, ge=5.0, le=50.0, description="Detour tolerance ceiling percentage (default 15%)")

class RouteSegment(BaseModel):
    start_coord: List[float]
    end_coord: List[float]
    length_meters: float
    multiplier: float
    lit: bool
    lighting_status: str = "lit"  # 'lit', 'unlit', 'unknown'
    highway_type: str
    surveillance: bool
    description: str
    patrol_verified: bool = False
    patrol_notes: Optional[str] = None
    nearby_place_name: Optional[str] = None

class SafetyEvidenceBreakdown(BaseModel):
    streetlighting: Dict[str, Any]
    nearby_active_places: Dict[str, Any]
    police_patrol: Dict[str, Any]
    hazards_and_closures: Dict[str, Any]
    specific_concerns: List[str] = []

class SafetyExplanation(BaseModel):
    estimated_walk_time_text: str
    safety_info_available: str
    recommendation_reason: str
    last_verified_text: str
    has_recent_patrol: bool = False
    patrol_officer: Optional[str] = None
    patrol_station: Optional[str] = None
    patrol_timestamp: Optional[str] = None
    patrol_freshness: str = "none"  # 'recent', 'outdated', 'expired', 'none'
    lighting_evidence: str
    reported_hazards: List[str] = []
    disclaimer: str = "These observations provide additional context, but they do not guarantee personal safety."

class RouteAlternative(BaseModel):
    id: str  # 'recommended_safe', 'alternative_route', 'direct_shortest'
    title: str
    route_type: str  # 'recommended', 'alternative', 'shortest'
    color: str
    distance_meters: float
    walk_time_minutes: float
    estimated_arrival_time: str
    illumination_pct: float
    safety_status: str  # 'Better-supported safety option', 'Caution', 'Insufficient data'
    coordinates: List[List[float]]
    warning_count: int
    summary: str
    safety_explanation: SafetyExplanation
    evidence_breakdown: SafetyEvidenceBreakdown
    segments: Optional[List[RouteSegment]] = None

class MultiRouteResponse(BaseModel):
    status: str
    origin_name: str
    destination_name: str
    origin_coords: List[float]
    destination_coords: List[float]
    routes: List[RouteAlternative]
    safe_havens: List[SafeHaven]
    active_hazards: List[Dict[str, Any]]
    verified_patrols: List[Dict[str, Any]]
    # Backward compatibility fields for legacy components
    direct_route: Optional[Dict[str, Any]] = None
    safe_route: Optional[Dict[str, Any]] = None
    detour_budget_pct: Optional[float] = 15.0
    detour_ceiling_meters: Optional[float] = 0.0
    detour_actual_pct: Optional[float] = 0.0

# Backward compatibility alias
RouteResponse = MultiRouteResponse
RouteResult = RouteAlternative

class PresetRoute(BaseModel):
    id: str
    title: str
    subtitle: str
    origin_name: str
    origin_coords: List[float]
    destination_name: str
    destination_coords: List[float]
    default_detour_budget_pct: float = 15.0
    description: str

class AuthLoginRequest(BaseModel):
    username: str
    password: str

class AuthRegisterRequest(BaseModel):
    username: str
    password: str
    full_name: str
    email: Optional[str] = None
    role: Optional[str] = "public"

class LogoutRequest(BaseModel):
    token: Optional[str] = None

class AuthUserResponse(BaseModel):
    id: int
    username: str
    role: str  # 'public', 'police', 'admin'
    full_name: str
    badge_number: Optional[str] = None
    station: Optional[str] = None
    token: str

class PatrolStartRequest(BaseModel):
    station: Optional[str] = None
    notes: Optional[str] = None

class PatrolRecordRequest(BaseModel):
    patrol_session_id: str
    latitude: float
    longitude: float

class PatrolSubmitRequest(BaseModel):
    patrol_session_id: str
    location_name: str
    route_coords: List[List[float]]
    lighting_condition: str  # 'well_lit', 'partially_lit', 'unlit', 'unknown'
    road_condition: str  # 'normal', 'under_construction', 'closed', 'caution'
    visible_hazards: str  # 'none', 'poor_lighting', 'construction', 'isolated_stretch', 'stray_dogs', 'waterlogging'
    notes: Optional[str] = None

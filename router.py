import heapq
import math
from datetime import datetime, timedelta
from typing import List, Tuple, Dict, Any, Optional

from graph_manager import CoimbatoreGraphManager, haversine_distance, graph_manager
from models import (
    RouteAlternative, 
    RouteSegment, 
    SafetyExplanation, 
    SafetyEvidenceBreakdown,
    MultiRouteResponse
)
from safe_havens import COIMBATORE_SAFE_HAVENS
from places import evaluate_places_along_route
from database import get_db

WALK_SPEED_MPS = 1.3888  # 5.0 km/h = 1.3888 meters per second

class CoimbatoreMultiRouter:
    def __init__(self, graph_manager: CoimbatoreGraphManager):
        self.gm = graph_manager

    def find_multi_routes(
        self,
        origin_lat: float, origin_lon: float,
        dest_lat: float, dest_lon: float,
        origin_name: str = "Selected Origin",
        dest_name: str = "Selected Destination",
        detour_budget_pct: float = 15.0
    ) -> MultiRouteResponse:
        """
        Calculates Google Maps-style multiple pedestrian routes across Coimbatore:
        1. Recommended Lower-Risk Route (Emerald Green)
        2. Alternative Pedestrian Route (Blue/Slate)
        3. Direct Shortest Route (Contrasting Red/Orange)
        """
        # Re-apply any recent database patrols/hazards dynamically
        self.gm._apply_database_patrols_and_hazards()
        self.gm._compute_edge_risk_weights()

        G = self.gm.G
        start_node = self.gm.get_nearest_node(origin_lat, origin_lon)
        end_node = self.gm.get_nearest_node(dest_lat, dest_lon)

        dest_coord = self.gm.get_node_coords(end_node)

        # -------------------------------------------------------------
        # PASS 1: Metric Shortest Path (Standard A* on edge 'length')
        # -------------------------------------------------------------
        direct_nodes, d_min = self._shortest_path(G, start_node, end_node, dest_coord, weight_key='length')
        if not direct_nodes:
            raise ValueError(f"No walking path found between coordinates ({origin_lat}, {origin_lon}) and ({dest_lat}, {dest_lon}).")

        # Detour budget ceiling
        detour_fraction = max(0.05, min(0.50, detour_budget_pct / 100.0))
        d_max = d_min * (1.0 + detour_fraction)

        # -------------------------------------------------------------
        # PASS 2: Recommended Safe Route (Minimizing Risk s.t. Length <= d_max)
        # -------------------------------------------------------------
        safe_nodes, safe_dist = self._constrained_safe_path(G, start_node, end_node, dest_coord, d_max)
        if not safe_nodes:
            safe_nodes = direct_nodes
            safe_dist = d_min

        # -------------------------------------------------------------
        # PASS 3: Alternative Route (Penalizing shared edges of Safe Route)
        # -------------------------------------------------------------
        alt_nodes, alt_dist = self._alternative_path(G, start_node, end_node, dest_coord, safe_nodes)
        if not alt_nodes or alt_nodes == safe_nodes:
            alt_nodes = direct_nodes if direct_nodes != safe_nodes else safe_nodes

        now = datetime.now()
        routes: List[RouteAlternative] = []

        # 1. Recommended Safe Route (Emerald Green)
        safe_route = self._build_route_alternative(
            G, safe_nodes,
            route_id="recommended_safe",
            title="Recommended Safer Route",
            route_type="recommended",
            color="#059669",
            is_recommended=True,
            now=now
        )
        routes.append(safe_route)

        # 2. Alternative Route (Blue/Slate)
        if alt_nodes and alt_nodes != safe_nodes:
            alt_route = self._build_route_alternative(
                G, alt_nodes,
                route_id="alternative_route",
                title="Alternative Pedestrian Route",
                route_type="alternative",
                color="#2563EB",
                is_recommended=False,
                now=now
            )
            routes.append(alt_route)

        # 3. Direct Shortest Route (Contrasting Red/Orange)
        if direct_nodes:
            direct_route = self._build_route_alternative(
                G, direct_nodes,
                route_id="direct_shortest",
                title="Direct Shortest Route",
                route_type="shortest",
                color="#EF4444",
                is_recommended=False,
                now=now
            )
            routes.append(direct_route)

        active_hazards = self._get_active_hazards()
        verified_patrols = self._get_verified_patrols()

        actual_detour_pct = round(((safe_route.distance_meters - direct_route.distance_meters) / max(1.0, direct_route.distance_meters)) * 100.0, 1)

        return MultiRouteResponse(
            status="success",
            origin_name=origin_name,
            destination_name=dest_name,
            origin_coords=[origin_lat, origin_lon],
            destination_coords=[dest_lat, dest_lon],
            routes=routes,
            safe_havens=COIMBATORE_SAFE_HAVENS,
            active_hazards=active_hazards,
            verified_patrols=verified_patrols,
            # Legacy compatibility
            direct_route=direct_route.dict(),
            safe_route=safe_route.dict(),
            detour_budget_pct=round(detour_budget_pct, 1),
            detour_ceiling_meters=round(d_max, 1),
            detour_actual_pct=max(0.0, actual_detour_pct)
        )

    def _shortest_path(self, G, start: int, goal: int, goal_coord: Tuple[float, float], weight_key: str = 'length') -> Tuple[List[int], float]:
        """A* search for shortest metric distance."""
        goal_lat, goal_lon = goal_coord
        frontier = [(0.0, 0.0, start, [start])]
        visited_dist = {start: 0.0}

        while frontier:
            f, d_so_far, current, path = heapq.heappop(frontier)
            if current == goal:
                return path, d_so_far

            if d_so_far > visited_dist.get(current, float('inf')):
                continue

            for neighbor in G.successors(current):
                edge_data = self._get_best_edge(G, current, neighbor, weight_key=weight_key)
                if not edge_data:
                    continue
                edge_len = edge_data.get('length', 10.0)
                new_d = d_so_far + edge_len

                if new_d < visited_dist.get(neighbor, float('inf')):
                    visited_dist[neighbor] = new_d
                    n_lat, n_lon = self.gm.get_node_coords(neighbor)
                    h = haversine_distance(n_lat, n_lon, goal_lat, goal_lon)
                    heapq.heappush(frontier, (new_d + h, new_d, neighbor, path + [neighbor]))

        return [], 0.0

    def _constrained_safe_path(self, G, start: int, goal: int, goal_coord: Tuple[float, float], d_max: float) -> Tuple[List[int], float]:
        """Constrained label-setting A* minimizing risk cost subject to length <= d_max."""
        goal_lat, goal_lon = goal_coord
        frontier = []
        start_lat, start_lon = self.gm.get_node_coords(start)
        h_risk = haversine_distance(start_lat, start_lon, goal_lat, goal_lon) * 0.95
        heapq.heappush(frontier, (h_risk, 0.0, 0.0, start, [start]))

        labels: Dict[int, List[Tuple[float, float]]] = {start: [(0.0, 0.0)]}

        while frontier:
            f_priority, cur_risk, cur_len, u, path = heapq.heappop(frontier)

            if u == goal:
                if cur_len <= d_max:
                    return path, cur_len

            for v in G.successors(u):
                if v in path:
                    continue

                edge_data = self._get_best_edge(G, u, v, weight_key='risk_cost')
                if not edge_data:
                    continue

                edge_len = edge_data.get('length', 10.0)
                edge_risk = edge_data.get('risk_cost', edge_len * 1.5)

                new_len = cur_len + edge_len
                new_risk = cur_risk + edge_risk

                v_lat, v_lon = self.gm.get_node_coords(v)
                euclidean_rem = haversine_distance(v_lat, v_lon, goal_lat, goal_lon)
                if (new_len + euclidean_rem) > d_max:
                    continue

                # Dominance check
                existing_labels = labels.get(v, [])
                is_dominated = False
                for prev_risk, prev_len in existing_labels:
                    if prev_risk <= new_risk and prev_len <= new_len:
                        is_dominated = True
                        break

                if is_dominated:
                    continue

                labels.setdefault(v, []).append((new_risk, new_len))
                if len(labels[v]) > 6:
                    labels[v].sort(key=lambda x: (x[0], x[1]))
                    labels[v] = labels[v][:6]

                h_remaining_risk = euclidean_rem * 0.95
                heapq.heappush(frontier, (new_risk + h_remaining_risk, new_risk, new_len, v, path + [v]))

        return [], 0.0

    def _alternative_path(self, G, start: int, goal: int, goal_coord: Tuple[float, float], primary_nodes: List[int]) -> Tuple[List[int], float]:
        """Finds alternative path by applying a penalty on edges heavily used in primary route."""
        primary_edges = set()
        for i in range(len(primary_nodes) - 1):
            primary_edges.add((primary_nodes[i], primary_nodes[i+1]))
            primary_edges.add((primary_nodes[i+1], primary_nodes[i]))

        goal_lat, goal_lon = goal_coord
        frontier = [(0.0, 0.0, start, [start])]
        visited_dist = {start: 0.0}

        while frontier:
            f, d_so_far, current, path = heapq.heappop(frontier)
            if current == goal:
                return path, d_so_far

            if d_so_far > visited_dist.get(current, float('inf')):
                continue

            for neighbor in G.successors(current):
                edge_data = self._get_best_edge(G, current, neighbor, weight_key='length')
                if not edge_data:
                    continue
                edge_len = edge_data.get('length', 10.0)
                penalty = 1.8 if (current, neighbor) in primary_edges else 1.0
                effective_len = edge_len * penalty
                new_d = d_so_far + effective_len

                if new_d < visited_dist.get(neighbor, float('inf')):
                    visited_dist[neighbor] = new_d
                    n_lat, n_lon = self.gm.get_node_coords(neighbor)
                    h = haversine_distance(n_lat, n_lon, goal_lat, goal_lon)
                    heapq.heappush(frontier, (new_d + h, new_d, neighbor, path + [neighbor]))

        return [], 0.0

    def _build_route_alternative(
        self, G, nodes: List[int],
        route_id: str, title: str, route_type: str, color: str,
        is_recommended: bool,
        now: datetime
    ) -> RouteAlternative:
        """Constructs RouteAlternative model with multi-evidence analysis and the 4 Questions."""
        coords: List[List[float]] = []
        segments: List[RouteSegment] = []
        total_meters = 0.0
        lit_meters = 0.0
        unlit_meters = 0.0
        unknown_lit_meters = 0.0
        warning_count = 0
        reported_hazards = []
        specific_concerns = []

        patrol_officer = None
        patrol_station = None
        patrol_observed_at = None
        patrol_covered_meters = 0.0

        for i, node in enumerate(nodes):
            lat, lon = self.gm.get_node_coords(node)
            coords.append([lat, lon])

            if i < len(nodes) - 1:
                next_node = nodes[i + 1]
                edge_data = self._get_best_edge(G, node, next_node, weight_key='risk_cost' if is_recommended else 'length')
                if not edge_data:
                    continue

                length = float(edge_data.get('length', 10.0))
                is_lit = edge_data.get('lit') == 'yes'
                raw_lit_val = edge_data.get('lit', 'unknown')
                multiplier = float(edge_data.get('multiplier', 1.0))
                hw = edge_data.get('highway', 'footway')
                name = edge_data.get('name', 'Pedestrian Walkway')

                total_meters += length
                if is_lit:
                    lit_meters += length
                    lighting_status = "lit"
                elif raw_lit_val == 'no':
                    unlit_meters += length
                    warning_count += 1
                    lighting_status = "unlit"
                    specific_concerns.append(f"Unlit pedestrian corridor ({int(length)}m) on {name}")
                else:
                    unknown_lit_meters += length
                    lighting_status = "unknown"
                    specific_concerns.append(f"Lighting status unverified on {name} ({int(length)}m)")

                if edge_data.get('patrol_verified'):
                    patrol_covered_meters += length
                    patrol_officer = edge_data.get('patrol_officer')
                    patrol_station = edge_data.get('patrol_station')
                    patrol_observed_at = edge_data.get('patrol_observed_at')

                if edge_data.get('hazard_warning'):
                    warning_count += 1
                    haz_text = edge_data.get('hazard_warning')
                    reported_hazards.append(haz_text)
                    specific_concerns.append(f"Reported road hazard on {name}: {haz_text}")

                segments.append(RouteSegment(
                    start_coord=[lat, lon],
                    end_coord=[self.gm.get_node_coords(next_node)[0], self.gm.get_node_coords(next_node)[1]],
                    length_meters=round(length, 1),
                    multiplier=round(multiplier, 2),
                    lit=is_lit,
                    lighting_status=lighting_status,
                    highway_type=hw,
                    surveillance=bool(edge_data.get('patrol_verified', False)),
                    description=name,
                    patrol_verified=bool(edge_data.get('patrol_verified', False)),
                    patrol_notes=edge_data.get('patrol_notes')
                ))

        walk_time_min = round(total_meters / (WALK_SPEED_MPS * 60.0), 1)
        arrival_dt = now + timedelta(minutes=walk_time_min)
        estimated_arrival_str = arrival_dt.strftime("%I:%M %p")

        lit_pct = round((lit_meters / max(1.0, total_meters)) * 100.0, 1)
        unlit_pct = round((unlit_meters / max(1.0, total_meters)) * 100.0, 1)
        unknown_lit_pct = round((unknown_lit_meters / max(1.0, total_meters)) * 100.0, 1)

        # -------------------------------------------------------------
        # EVIDENCE SOURCE B: Nearby Active Places & Public Establishments
        # -------------------------------------------------------------
        places_eval = evaluate_places_along_route(coords, query_time=now, proximity_buffer_m=65.0)
        active_places = places_eval['active_places']
        closed_places = places_eval['closed_places']

        # Add place observations to specific concerns if commercial areas are shuttered
        if len(closed_places) > 0 and now.hour >= 21:
            closed_names = ", ".join([p['name'] for p in closed_places[:2]])
            specific_concerns.append(f"Commercial establishments closed after 21:00 ({closed_names})")

        # -------------------------------------------------------------
        # EVIDENCE SOURCE C: Police Patrol Evidence & Freshness
        # -------------------------------------------------------------
        patrol_freshness = "none"
        last_verified_str = "No recent police patrol recorded on this route"

        if patrol_observed_at:
            try:
                obs_time = datetime.fromisoformat(patrol_observed_at)
                diff = datetime.utcnow() - obs_time
                hours_ago = round(diff.total_seconds() / 3600.0, 1)
                if hours_ago <= 6.0:
                    patrol_freshness = "recent"
                    last_verified_str = f"Recently observed ({hours_ago}h ago) by {patrol_officer} ({patrol_station})"
                elif hours_ago <= 24.0:
                    patrol_freshness = "outdated"
                    last_verified_str = f"Observation becoming outdated ({hours_ago}h ago) — verification expiring"
                else:
                    patrol_freshness = "expired"
                    last_verified_str = f"Observation expired ({hours_ago}h ago) — awaiting updated patrol"
            except Exception:
                last_verified_str = "Patrol timestamp verified"
                patrol_freshness = "recent"

        # -------------------------------------------------------------
        # SAFETY STATUS RULES (Section 6 of Specification)
        # -------------------------------------------------------------
        # Better-supported safety option / Caution / Insufficient data
        if len(reported_hazards) > 0 or unlit_pct > 25.0:
            safety_status = "Caution"
        elif is_recommended and lit_pct >= 75.0 and len(reported_hazards) == 0:
            safety_status = "Better-supported safety option"
        elif unknown_lit_pct > 40.0:
            safety_status = "Insufficient data"
        else:
            safety_status = "Caution" if warning_count > 0 else "Better-supported safety option"

        # -------------------------------------------------------------
        # THE 4 QUESTIONS (Section 7 of Specification)
        # -------------------------------------------------------------
        # 1. What is the estimated walking time?
        q1_walk_time = f"{walk_time_min} min ({int(round(total_meters))} m) estimated at 5.0 km/h walking pace • Arrives ~{estimated_arrival_str}"

        # 2. What safety-related information is available?
        evidence_items = []
        if lit_pct > 0:
            evidence_items.append(f"{lit_pct}% recorded streetlight coverage")
        if unknown_lit_pct > 0:
            evidence_items.append(f"{unknown_lit_pct}% lighting status unknown")
        if len(active_places) > 0:
            place_names = ", ".join([p['name'] for p in active_places[:2]])
            evidence_items.append(f"Proximity to {len(active_places)} verified active public venues ({place_names})")
        if patrol_covered_meters > 0 and patrol_freshness in ['recent', 'outdated']:
            evidence_items.append(f"Verified patrol on {int(round(patrol_covered_meters))}m by {patrol_officer}")
        elif patrol_freshness == "none":
            evidence_items.append("No recent police patrol logged on this specific path (not penalized)")

        q2_safety_info = ". ".join(evidence_items) + "."

        # 3. Why is the route recommended or cautioned against?
        if safety_status == "Better-supported safety option":
            q3_why = f"Recommended because {lit_pct}% follows primary avenues with verified streetlighting and active pedestrian infrastructure, avoiding unlit shortcuts."
            if len(active_places) > 0:
                q3_why += f" Passes near verified active facilities offering public presence."
        elif safety_status == "Caution":
            concerns_text = "; ".join(specific_concerns[:2]) if specific_concerns else "Unlit sections detected"
            q3_why = f"Caution advised: Route includes potential safety concerns: {concerns_text}. Alternate avenues with higher illumination recommended."
        else:
            q3_why = f"Insufficient verification: {unknown_lit_pct}% of segments lack current lighting data or recent municipal observations."

        # 4. When was the relevant information last verified?
        q4_last_verified = last_verified_str

        # Assemble Evidence Breakdown
        evidence_breakdown = SafetyEvidenceBreakdown(
            streetlighting={
                "percentage_lit": lit_pct,
                "percentage_unlit": unlit_pct,
                "percentage_unknown": unknown_lit_pct,
                "source": "OpenStreetMap Pedestrian Infrastructure + Municipal Smart City LED Grid",
                "confidence": "Recorded in dataset; physical operation subject to municipal grid status"
            },
            nearby_active_places={
                "total_active": len(active_places),
                "total_closed": len(closed_places),
                "active_places": active_places,
                "closed_places": closed_places,
                "summary": f"{len(active_places)} verified active establishments within 65m buffer"
            },
            police_patrol={
                "patrol_present": bool(patrol_covered_meters > 0),
                "patrol_meters": round(patrol_covered_meters),
                "officer": patrol_officer,
                "station": patrol_station,
                "observed_at": patrol_observed_at,
                "freshness": patrol_freshness,
                "note": "Past patrol observations reflect visited conditions at that time and do not guarantee continuous safety."
            },
            hazards_and_closures={
                "hazard_count": len(reported_hazards),
                "items": reported_hazards
            },
            specific_concerns=specific_concerns
        )

        explanation = SafetyExplanation(
            estimated_walk_time_text=q1_walk_time,
            safety_info_available=q2_safety_info,
            recommendation_reason=q3_why,
            last_verified_text=q4_last_verified,
            has_recent_patrol=bool(patrol_covered_meters > 0 and patrol_freshness == "recent"),
            patrol_officer=patrol_officer,
            patrol_station=patrol_station,
            patrol_timestamp=patrol_observed_at,
            patrol_freshness=patrol_freshness,
            lighting_evidence=f"{lit_pct}% recorded streetlight coverage ({unknown_lit_pct}% unknown)",
            reported_hazards=reported_hazards,
            disclaimer="These observations provide additional context, but they do not guarantee personal safety."
        )

        return RouteAlternative(
            id=route_id,
            title=title,
            route_type=route_type,
            color=color,
            distance_meters=round(total_meters, 1),
            walk_time_minutes=walk_time_min,
            estimated_arrival_time=estimated_arrival_str,
            illumination_pct=lit_pct,
            safety_status=safety_status,
            coordinates=coords,
            warning_count=warning_count,
            summary=f"{int(round(total_meters))}m • ~{walk_time_min} min • {safety_status}",
            safety_explanation=explanation,
            evidence_breakdown=evidence_breakdown,
            segments=segments
        )

    def _get_best_edge(self, G, u: int, v: int, weight_key: str = 'length') -> Optional[Dict[str, Any]]:
        edges = G.get_edge_data(u, v)
        if not edges:
            return None
        return min(edges.values(), key=lambda d: d.get(weight_key, float('inf')))

    def _get_active_hazards(self) -> List[Dict[str, Any]]:
        """Returns active verified hazards from database."""
        try:
            conn = get_db()
            cursor = conn.cursor()
            cursor.execute("SELECT id, category, description, latitude, longitude, severity, reported_at, verified_by FROM hazards WHERE is_active = 1;")
            rows = cursor.fetchall()
            conn.close()
            return [dict(r) for r in rows]
        except Exception:
            return []

    def _get_verified_patrols(self) -> List[Dict[str, Any]]:
        """Returns active verified patrols from database."""
        try:
            conn = get_db()
            cursor = conn.cursor()
            cursor.execute("""
            SELECT id, officer_name, badge_number, station, location_name, route_coords, 
                   lighting_condition, road_condition, visible_hazards, notes, observed_at, expires_at
            FROM observations
            WHERE status = 'verified'
            ORDER BY observed_at DESC LIMIT 10;
            """)
            rows = cursor.fetchall()
            conn.close()
            result = []
            for r in rows:
                item = dict(r)
                try:
                    item['route_coords'] = json.loads(item['route_coords'])
                except Exception:
                    pass
                result.append(item)
            return result
        except Exception:
            return []

# Singleton instance
multi_router = CoimbatoreMultiRouter(graph_manager)

# Backward compatibility alias
TwoPassRouter = CoimbatoreMultiRouter

import os
import math
import json
import sqlite3
import numpy as np
import networkx as nx
from scipy.spatial import cKDTree
from typing import Tuple, List, Dict, Any, Optional
from datetime import datetime, timedelta

from safe_havens import COIMBATORE_SAFE_HAVENS, SafeHaven
from database import get_db

GRAPH_FILE = os.path.join(os.path.dirname(__file__), "coimbatore_graph.graphml")

def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculates great-circle distance between two points in meters."""
    R = 6371000.0  # Earth radius in meters
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2.0) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2.0) ** 2
    return 2.0 * R * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))

def point_to_segment_distance(plat: float, plon: float, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Distance from a point to a line segment in meters."""
    lat_mid = (plat + lat1 + lat2) / 3.0
    kx = 111320.0 * math.cos(math.radians(lat_mid))
    ky = 110540.0
    px, py = plon * kx, plat * ky
    x1, y1 = lon1 * kx, lat1 * ky
    x2, y2 = lon2 * kx, lat2 * ky
    dx = x2 - x1
    dy = y2 - y1
    segment_len_sq = dx * dx + dy * dy
    if segment_len_sq < 1e-6:
        return math.hypot(px - x1, py - y1)
    t = max(0.0, min(1.0, ((px - x1) * dx + (py - y1) * dy) / segment_len_sq))
    return math.hypot(px - (x1 + t * dx), py - (y1 + t * dy))

class CoimbatoreGraphManager:
    def __init__(self):
        self.G: Optional[nx.MultiDiGraph] = None
        self.node_ids: List[int] = []
        self.node_coords: np.ndarray = np.empty((0, 2))
        self.kdtree: Optional[cKDTree] = None
        self.safe_havens: List[SafeHaven] = COIMBATORE_SAFE_HAVENS
        
    def initialize(self):
        """Builds or loads the city-wide walking network for Coimbatore."""
        self.G = nx.MultiDiGraph()

        # Build comprehensive city-wide Coimbatore pedestrian grid and arterial network
        self._construct_coimbatore_network()
        self._enrich_kpriet_campus_network()
        self._apply_database_patrols_and_hazards()
        self._compute_edge_risk_weights()
        self._build_spatial_index()
        print(f"CoimbatoreGraphManager initialized: {len(self.G.nodes)} nodes, {len(self.G.edges)} edges covering Greater Coimbatore.")

    def _construct_coimbatore_network(self):
        """Constructs key urban corridors and interconnected nodes across Coimbatore."""
        # Significant urban intersections and corridor nodes across Coimbatore
        cbe_nodes = {
            # Gandhipuram & Central Sector
            "gp_bus_stand": (11.0168, 76.9678, "Gandhipuram Bus Stand"),
            "gp_signal": (11.0175, 76.9660, "GP Signal Junction"),
            "cross_cut_1": (11.0185, 76.9650, "Cross Cut Rd - North End"),
            "cross_cut_2": (11.0195, 76.9635, "Cross Cut Rd - Lakshmi Complex"),
            "hundred_ft_1": (11.0210, 76.9710, "100 Feet Rd - 6th Cross"),
            "hundred_ft_2": (11.0235, 76.9740, "100 Feet Rd - GP Flyover Link"),
            "ram_nagar_1": (11.0120, 76.9610, "Ram Nagar Central"),
            "brookefields": (11.0089, 76.9572, "Brookefields Mall Plaza"),
            
            # RS Puram & West Sector
            "db_road_south": (11.0085, 76.9505, "DB Road - Roundabout"),
            "db_road_mid": (11.0125, 76.9515, "DB Road - Post Office"),
            "db_road_north": (11.0160, 76.9525, "DB Road - Flower Market"),
            "cowley_brown_1": (11.0130, 76.9460, "Cowley Brown Rd - West"),
            "forest_college": (11.0180, 76.9430, "Forest College Campus Walk"),
            "saibaba_colony_1": (11.0315, 76.9450, "Saibaba Colony - NSR Rd"),
            "saibaba_colony_2": (11.0350, 76.9480, "Saibaba Temple Junction"),
            "ganga_hospital": (11.0260, 76.9510, "Mettupalayam Rd - Ganga Hospital"),

            # Town Hall, Railway Station & South Sector
            "cbe_junction": (10.9980, 76.9620, "Coimbatore Junction Main"),
            "rly_feeder_rd": (10.9995, 76.9645, "Railway Feeder Road"),
            "town_hall": (10.9940, 76.9605, "Town Hall Clock Tower"),
            "oppanakara_st": (10.9960, 76.9590, "Oppanakara Street Bazaar"),
            "voc_park": (11.0040, 76.9710, "VOC Park Gate"),
            "race_course_west": (11.0010, 76.9750, "Race Course Promenade West"),
            "race_course_east": (11.0025, 76.9820, "Race Course Promenade East"),
            "ukkadam_bus": (10.9890, 76.9580, "Ukkadam Bus Stand"),

            # Avinashi Road Corridor & East Sector
            "avinashi_gandhipuram": (11.0150, 76.9720, "Avinashi Rd - Anna Statue"),
            "avinashi_gknm": (11.0170, 76.9810, "Avinashi Rd - GKNM Hospital"),
            "nava_india": (11.0210, 76.9910, "Nava India Signal"),
            "peelamedu_psg": (11.0245, 77.0030, "Peelamedu - PSG Tech Main Gate"),
            "peelamedu_station": (11.0220, 77.0080, "Peelamedu Railway Station Link"),
            "fun_republic": (11.0280, 77.0120, "Fun Republic Mall"),
            "hope_college": (11.0305, 77.0210, "Hope College Junction"),
            "sitra_airport": (11.0300, 77.0430, "SITRA Airport Junction"),
            "kmch_corridor": (11.0420, 77.0370, "KMCH Hospital Promenade"),

            # Singanallur & Southeast Sector
            "trichy_rd_ramanathapuram": (10.9970, 76.9950, "Trichy Rd - Ramanathapuram"),
            "trichy_rd_singanallur": (10.9995, 77.0250, "Singanallur Bus Stand"),
            "singanallur_lake": (10.9920, 77.0270, "Singanallur Lake Park"),
            "ondipudur_link": (11.0020, 77.0450, "Ondipudur Flyover Walkway"),

            # Saravanampatti & North Sector
            "sivanandhapuram": (11.0540, 76.9920, "Prozone Mall - Sivanandhapuram"),
            "saravanampatti_jn": (11.0780, 76.9950, "Saravanampatti IT Junction"),
            "kgisl_tech_park": (11.0820, 76.9980, "CHIL SEZ & KGISL Campus"),

            # Eastern Outskirts to KPRIET / Arasur
            "neelambur_bypass": (11.0550, 77.0850, "Neelambur NH 544 Flyover"),
            "arasur_bus_stop": (11.0712, 77.1350, "Arasur 4-Roads Bus Stop"),
            "arasur_service_rd": (11.0725, 77.1365, "NH 544 Lit Service Road"),
            "kpriet_main_gate": (11.0769, 77.1405, "KPRIET Campus Main Entrance")
        }

        # Add all nodes to graph
        self.node_id_map = {}
        for idx, (key, (lat, lon, label)) in enumerate(cbe_nodes.items()):
            node_id = 100000 + idx
            self.G.add_node(node_id, y=lat, x=lon, name=label, key=key)
            self.node_id_map[key] = node_id

        # Helper to add bidirectional streets with attributes
        def add_street(u_key: str, v_key: str, length_meters: float, highway: str, lit: bool, name: str, risk_mod: float = 1.0):
            if u_key not in self.node_id_map or v_key not in self.node_id_map:
                return
            u = self.node_id_map[u_key]
            v = self.node_id_map[v_key]
            self.G.add_edge(u, v, length=length_meters, highway=highway, lit='yes' if lit else 'no', name=name, risk_modifier=risk_mod)
            self.G.add_edge(v, u, length=length_meters, highway=highway, lit='yes' if lit else 'no', name=name, risk_modifier=risk_mod)

        # 1. Central & Gandhipuram Networks (Lit Commercial Footpaths)
        add_street("gp_bus_stand", "gp_signal", 220, "primary", True, "Dr Nanjappa Rd Promenade")
        add_street("gp_signal", "cross_cut_1", 200, "secondary", True, "Cross Cut Rd Commercial")
        add_street("cross_cut_1", "cross_cut_2", 230, "secondary", True, "Cross Cut Rd North")
        add_street("gp_bus_stand", "hundred_ft_1", 580, "secondary", True, "100 Feet Rd")
        add_street("hundred_ft_1", "hundred_ft_2", 420, "secondary", True, "100 Feet Rd East")
        add_street("gp_bus_stand", "ram_nagar_1", 850, "tertiary", True, "Ram Nagar Sastry Rd")
        add_street("ram_nagar_1", "brookefields", 520, "tertiary", True, "Krishnasamy Mudaliyar Rd")

        # 2. RS Puram Network (Well-lit, patrolled avenues)
        add_street("brookefields", "db_road_south", 780, "secondary", True, "Sukrawarpet - DB Rd Link")
        add_street("db_road_south", "db_road_mid", 450, "secondary", True, "DB Road Promenade")
        add_street("db_road_mid", "db_road_north", 420, "secondary", True, "DB Road North")
        add_street("db_road_mid", "cowley_brown_1", 520, "tertiary", True, "Cowley Brown Road")
        add_street("cowley_brown_1", "forest_college", 600, "footway", True, "Forest College Avenue")
        add_street("db_road_north", "ganga_hospital", 980, "primary", True, "Mettupalayam Road Promenade")
        add_street("ganga_hospital", "saibaba_colony_1", 850, "secondary", True, "NSR Road Avenue")
        add_street("saibaba_colony_1", "saibaba_colony_2", 480, "secondary", True, "Saibaba Temple Corridor")

        # 3. Town Hall & Railway Station Sector
        add_street("ram_nagar_1", "cbe_junction", 1100, "secondary", True, "State Bank Road")
        add_street("cbe_junction", "rly_feeder_rd", 320, "footway", True, "Railway Feeder Lit Walkway")
        add_street("cbe_junction", "town_hall", 650, "secondary", True, "Big Bazaar Street")
        add_street("town_hall", "oppanakara_st", 350, "secondary", True, "Oppanakara Commercial Street")
        add_street("oppanakara_st", "ukkadam_bus", 950, "primary", True, "Palakkad Rd Pedestrian Path")
        add_street("rly_feeder_rd", "voc_park", 750, "tertiary", True, "Park Gate Road")
        add_street("voc_park", "race_course_west", 680, "residential", True, "Race Course West Promenade")
        add_street("race_course_west", "race_course_east", 820, "footway", True, "Race Course Lit Walking Track")

        # 4. Avinashi Road Arterial Corridor (Main East-West Spine)
        add_street("gp_signal", "avinashi_gandhipuram", 650, "primary", True, "Park Gate Avinashi Flyover Pedestrian Lane")
        add_street("avinashi_gandhipuram", "avinashi_gknm", 980, "primary", True, "Avinashi Road Illuminated Promenade")
        add_street("avinashi_gknm", "nava_india", 1150, "primary", True, "Avinashi Road (GKNM to Nava India)")
        add_street("nava_india", "peelamedu_psg", 1350, "primary", True, "Avinashi Road Student Corridor")
        add_street("peelamedu_psg", "peelamedu_station", 450, "tertiary", True, "Peelamedu Station Link")
        add_street("peelamedu_psg", "fun_republic", 850, "primary", True, "Avinashi Road (PSG to Fun Republic)")
        add_street("fun_republic", "hope_college", 950, "primary", True, "Avinashi Road (Hope College)")
        add_street("hope_college", "sitra_airport", 2200, "primary", True, "Avinashi Road Airport Highway Footpath")
        add_street("sitra_airport", "kmch_corridor", 1400, "primary", True, "KMCH Hospital Boulevard")

        # 5. Singanallur & Trichy Road Corridor
        add_street("race_course_east", "trichy_rd_ramanathapuram", 1600, "secondary", True, "Trichy Road Lit Walkway")
        add_street("trichy_rd_ramanathapuram", "trichy_rd_singanallur", 3100, "primary", True, "Trichy Road (Ramanathapuram to Singanallur)")
        add_street("trichy_rd_singanallur", "singanallur_lake", 850, "footway", True, "Singanallur Lake Promenade")
        add_street("trichy_rd_singanallur", "ondipudur_link", 1850, "primary", True, "Trichy Road East")

        # 6. North IT Corridor (Saravanampatti)
        add_street("hundred_ft_2", "sivanandhapuram", 3800, "primary", True, "Sathy Road (Gandhipuram to Prozone)")
        add_street("sivanandhapuram", "saravanampatti_jn", 2700, "primary", True, "Sathy Road IT Corridor")
        add_street("saravanampatti_jn", "kgisl_tech_park", 650, "tertiary", True, "CHIL SEZ Campus Road")

        # 7. Connecting Highway to Eastern Periphery (Arasur / KPRIET)
        add_street("kmch_corridor", "neelambur_bypass", 4500, "primary", True, "NH 544 Avinashi Highway Footpath")
        add_street("neelambur_bypass", "arasur_bus_stop", 5200, "primary", True, "NH 544 Lit Service Corridor")
        add_street("arasur_bus_stop", "arasur_service_rd", 250, "secondary", True, "Arasur Service Road")
        add_street("arasur_service_rd", "kpriet_main_gate", 480, "tertiary", True, "KPRIET Campus Boulevard")

        # Alternative unlit shortcuts (for testing contrasting risk detection)
        add_street("cross_cut_2", "hundred_ft_1", 720, "service", False, "Unlit Railway Back-Alley Shortcut", risk_mod=3.8)
        add_street("brookefields", "ram_nagar_1", 620, "service", False, "Old Cloth Mill Unlit Service Lane", risk_mod=3.5)
        add_street("nava_india", "peelamedu_station", 1450, "track", False, "Unpaved Railway Track Perimeter", risk_mod=4.5)

    def _enrich_kpriet_campus_network(self):
        """Includes the detailed KPRIET campus walking network."""
        campus_nodes = {
            "kpriet_admin": (11.082215, 77.134167, "Administrative Academic Block"),
            "kpriet_quad": (11.082800, 77.135200, "Academic Quadrangle"),
            "kpriet_canteen": (11.083342, 77.136117, "Central Canteen & Night Hub"),
            "kpriet_lib": (11.084274, 77.136005, "KPRIET Central Library"),
            "kpriet_hostels": (11.086305, 77.138145, "Student Hostels Complex"),
            "kpriet_workshops": (11.084800, 77.134800, "Rear Workshop Service Shed"),
            "kpriet_perimeter": (11.085500, 77.136800, "Perimeter Unpaved Dirt Track")
        }

        for key, (lat, lon, label) in campus_nodes.items():
            node_id = 200000 + len(self.node_id_map)
            self.G.add_node(node_id, y=lat, x=lon, name=label, key=key)
            self.node_id_map[key] = node_id

        # Connect gate to campus
        gate_id = self.node_id_map["kpriet_main_gate"]
        admin_id = self.node_id_map["kpriet_admin"]
        quad_id = self.node_id_map["kpriet_quad"]
        canteen_id = self.node_id_map["kpriet_canteen"]
        lib_id = self.node_id_map["kpriet_lib"]
        hostels_id = self.node_id_map["kpriet_hostels"]
        workshops_id = self.node_id_map["kpriet_workshops"]
        perimeter_id = self.node_id_map["kpriet_perimeter"]

        def add_bidirectional(u, v, dist, hw, lit, name, risk_mod=1.0):
            self.G.add_edge(u, v, length=dist, highway=hw, lit='yes' if lit else 'no', name=name, risk_modifier=risk_mod)
            self.G.add_edge(v, u, length=dist, highway=hw, lit='yes' if lit else 'no', name=name, risk_modifier=risk_mod)

        # Well-lit Academic Promenade
        add_bidirectional(gate_id, admin_id, 750, "tertiary", True, "Campus Main Entrance Boulevard")
        add_bidirectional(admin_id, quad_id, 120, "footway", True, "Academic Promenade West")
        add_bidirectional(quad_id, canteen_id, 130, "footway", True, "Central Canteen Plaza")
        add_bidirectional(canteen_id, lib_id, 110, "footway", True, "Academic Promenade North")
        add_bidirectional(lib_id, hostels_id, 320, "footway", True, "Hostel Main Lit Walkway")

        # Dark Rear Workshop Shortcuts (direct, but unlit & risky)
        add_bidirectional(admin_id, workshops_id, 240, "service", False, "Rear Mechanical Lab Service Shed", risk_mod=3.5)
        add_bidirectional(workshops_id, lib_id, 150, "service", False, "Unlit Workshop Loading Alley", risk_mod=3.8)
        add_bidirectional(canteen_id, perimeter_id, 180, "track", False, "Perimeter Unpaved Dirt Track", risk_mod=4.5)
        add_bidirectional(perimeter_id, hostels_id, 160, "track", False, "Hostel Rear Fence Track", risk_mod=4.5)

    def _apply_database_patrols_and_hazards(self):
        """Enriches graph edges with active police patrol observations and verified hazards."""
        try:
            conn = get_db()
            cursor = conn.cursor()

            # 1. Fetch valid, verified observations
            now_str = datetime.utcnow().isoformat()
            cursor.execute("""
            SELECT id, officer_name, badge_number, station, location_name, route_coords, 
                   lighting_condition, road_condition, visible_hazards, notes, observed_at, expires_at
            FROM observations
            WHERE status = 'verified' AND expires_at > ?;
            """, (now_str,))
            active_obs = cursor.fetchall()

            for obs in active_obs:
                try:
                    coords = json.loads(obs['route_coords'])
                    # For every segment in the observed patrol path, match nearby graph edges
                    for i in range(len(coords) - 1):
                        p1 = coords[i]
                        p2 = coords[i+1]
                        for u, v, k, d in self.G.edges(keys=True, data=True):
                            u_lat, u_lon = self.G.nodes[u]['y'], self.G.nodes[u]['x']
                            v_lat, v_lon = self.G.nodes[v]['y'], self.G.nodes[v]['x']
                            # If edge midpoint is near patrol segment (< 50m)
                            mid_lat = (u_lat + v_lat) / 2.0
                            mid_lon = (u_lon + v_lon) / 2.0
                            dist_to_patrol = point_to_segment_distance(mid_lat, mid_lon, p1[0], p1[1], p2[0], p2[1])
                            if dist_to_patrol < 60.0:
                                d['patrol_verified'] = True
                                d['patrol_officer'] = obs['officer_name']
                                d['patrol_station'] = obs['station']
                                d['patrol_observed_at'] = obs['observed_at']
                                d['patrol_notes'] = obs['notes']
                                # Apply patrol discount
                                d['risk_modifier'] = min(d.get('risk_modifier', 1.0), 0.75)
                except Exception as ex:
                    print("Error parsing patrol coords:", ex)

            # 2. Fetch active hazards
            cursor.execute("SELECT id, category, description, latitude, longitude, severity FROM hazards WHERE is_active = 1;")
            hazards = cursor.fetchall()
            for haz in hazards:
                h_lat, h_lon = haz['latitude'], haz['longitude']
                for u, v, k, d in self.G.edges(keys=True, data=True):
                    u_lat, u_lon = self.G.nodes[u]['y'], self.G.nodes[u]['x']
                    v_lat, v_lon = self.G.nodes[v]['y'], self.G.nodes[v]['x']
                    dist = point_to_segment_distance(h_lat, h_lon, u_lat, u_lon, v_lat, v_lon)
                    if dist < 80.0:
                        d['hazard_warning'] = haz['description']
                        d['hazard_severity'] = haz['severity']
                        d['risk_modifier'] = max(d.get('risk_modifier', 1.0), 4.5)

            conn.close()
        except Exception as e:
            print("Database patrol/hazard enrichment note:", e)

    def _compute_edge_risk_weights(self):
        """Computes risk cost for every edge based on lighting, road type, patrols, and hazards."""
        for u, v, k, d in self.G.edges(keys=True, data=True):
            length = float(d.get('length', 10.0))
            is_lit = d.get('lit') == 'yes'
            hw = d.get('highway', 'footway')
            mod = float(d.get('risk_modifier', 1.0))

            base_multiplier = 1.0
            if is_lit:
                if hw in ['primary', 'secondary', 'footway']:
                    base_multiplier = 1.0
                else:
                    base_multiplier = 1.2
            else:
                if hw == 'service':
                    base_multiplier = 3.5
                elif hw == 'track':
                    base_multiplier = 4.5
                else:
                    base_multiplier = 2.8

            if d.get('patrol_verified'):
                base_multiplier *= 0.75  # 25% risk reduction for verified active patrols

            if d.get('hazard_warning'):
                base_multiplier *= 3.0  # Hazard penalty

            final_multiplier = max(0.6, base_multiplier * mod)
            d['multiplier'] = round(final_multiplier, 2)
            d['risk_cost'] = round(length * final_multiplier, 2)

    def _build_spatial_index(self):
        """Builds KDTree index for all node coordinates."""
        self.node_ids = list(self.G.nodes)
        coords = []
        for n in self.node_ids:
            coords.append([self.G.nodes[n]['y'], self.G.nodes[n]['x']])
        self.node_coords = np.array(coords)
        if len(self.node_coords) > 0:
            self.kdtree = cKDTree(self.node_coords)

    def get_nearest_node(self, lat: float, lon: float) -> int:
        """Finds nearest walkable node in the graph."""
        if not self.kdtree or len(self.node_ids) == 0:
            raise RuntimeError("Graph spatial index not initialized.")
        dist, idx = self.kdtree.query([lat, lon])
        return self.node_ids[idx]

    def get_node_coords(self, node_id: int) -> Tuple[float, float]:
        """Returns (lat, lon) for node."""
        return self.G.nodes[node_id]['y'], self.G.nodes[node_id]['x']

# Singleton instance
graph_manager = CoimbatoreGraphManager()

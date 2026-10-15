from typing import List
from pydantic import BaseModel

class SafeHaven(BaseModel):
    id: str
    name: str
    type: str  # police_station, hospital_emergency, security_post, transit_hub
    lat: float
    lon: float
    description: str
    contact: str = "112"

COIMBATORE_SAFE_HAVENS: List[SafeHaven] = [
    SafeHaven(
        id="haven_cbe_central_police",
        name="Coimbatore Central Police Station (Gandhipuram)",
        type="police_station",
        lat=11.0180,
        lon=76.9680,
        description="24/7 Central City Police Station with active patrol dispatch, CCTV operations room, and walk-in assistance.",
        contact="0422-2300970"
    ),
    SafeHaven(
        id="haven_rspuram_police",
        name="RS Puram B2 Police Station (DB Road)",
        type="police_station",
        lat=11.0090,
        lon=76.9515,
        description="24/7 Western Zone police station with illuminated public safety kiosk and continuous officer presence.",
        contact="0422-2541333"
    ),
    SafeHaven(
        id="haven_peelamedu_police",
        name="Peelamedu E2 Police Station (Avinashi Road)",
        type="police_station",
        lat=11.0250,
        lon=77.0040,
        description="24/7 Eastern highway and student corridor police checkpoint with direct emergency phone link.",
        contact="0422-2573211"
    ),
    SafeHaven(
        id="haven_cbe_junction_rpf",
        name="Coimbatore Junction Railway Police & Help Desk",
        type="transit_hub",
        lat=10.9982,
        lon=76.9625,
        description="24/7 illuminated transit security station with active railway police patrol and high-traffic pedestrian surveillance.",
        contact="139"
    ),
    SafeHaven(
        id="haven_singanallur_police",
        name="Singanallur E1 Police Station (Trichy Road)",
        type="police_station",
        lat=10.9998,
        lon=77.0260,
        description="24/7 Southern arterial police post with emergency help booth and active highway patrols.",
        contact="0422-2572100"
    ),
    SafeHaven(
        id="haven_saibaba_police",
        name="Saibaba Colony B3 Police Station",
        type="police_station",
        lat=11.0320,
        lon=76.9440,
        description="24/7 North-Western sector police assistance center with round-the-clock duty officer.",
        contact="0422-2441222"
    ),
    SafeHaven(
        id="haven_kmch_emergency",
        name="KMCH Multi-Specialty Hospital 24/7 Emergency Center",
        type="hospital_emergency",
        lat=11.0420,
        lon=77.0370,
        description="24/7 trauma care and hospital security desk with high floodlighting and public emergency telephone.",
        contact="0422-4323800"
    ),
    SafeHaven(
        id="haven_psg_emergency",
        name="PSG Hospitals 24/7 Emergency Trauma Desk (Peelamedu)",
        type="hospital_emergency",
        lat=11.0240,
        lon=77.0020,
        description="24/7 medical triage center with security personnel, defibrillators, and illuminated waiting bays.",
        contact="0422-2570170"
    ),
    SafeHaven(
        id="haven_kpriet_sec_main",
        name="KPRIET Campus Main Security & Help Desk (Arasur)",
        type="security_post",
        lat=11.0771,
        lon=77.1405,
        description="24/7 staffed university entrance gate with security dispatch, emergency lighting, and first aid.",
        contact="0422-2635600"
    ),
    SafeHaven(
        id="haven_arasur_patrol",
        name="Arasur 4-Roads Police & Traffic Checkpoint (NH 544)",
        type="police_station",
        lat=11.0715,
        lon=77.1352,
        description="National Highway pedestrian assistance point with constant lighting and emergency roadside assistance.",
        contact="112"
    )
]

# Backward compatibility alias
CAMPUS_SAFE_HAVENS = COIMBATORE_SAFE_HAVENS

"""
Simulated ground-truth data for RescueNet AI.

In a production system this would live in PostgreSQL (static records) and
Redis (live availability), fed by real integrations (hospital management
systems, fleet telematics, NDRF resource registries, etc). For this project
we simulate a mid-size Indian metro area (default: Delhi) with a fixed set
of hospitals, shelters, resources, and volunteers so the pipeline has
something real to reason over.

`reset_state()` returns a fresh deep copy so the demo can be re-run cleanly.
"""
import copy

BASE_LAT, BASE_LON = 28.6139, 77.2090  # Delhi, matches the flood example in the brief

_DEFAULT_STATE = {
    "hospitals": [
        {"name": "AIIMS Trauma Center", "lat": 28.5672, "lon": 77.2100, "icu_beds": 6, "general_beds": 40, "ventilators": 10},
        {"name": "Safdarjung Hospital", "lat": 28.5691, "lon": 77.2064, "icu_beds": 2, "general_beds": 25, "ventilators": 4},
        {"name": "RML Hospital", "lat": 28.6259, "lon": 77.2007, "icu_beds": 8, "general_beds": 55, "ventilators": 12},
        {"name": "GTB Hospital", "lat": 28.6785, "lon": 77.3097, "icu_beds": 5, "general_beds": 30, "ventilators": 6},
    ],
    "shelters": [
        {"name": "Community Hall Shelter #12", "lat": 28.6100, "lon": 77.2300, "capacity": 300},
        {"name": "Government School Shelter #14", "lat": 28.6400, "lon": 77.1900, "capacity": 500},
        {"name": "Stadium Relief Camp", "lat": 28.5900, "lon": 77.2500, "capacity": 800},
    ],
    "resources": {
        "ambulance": [
            {"id": "AMB-01", "lat": 28.6050, "lon": 77.2150, "available": True},
            {"id": "AMB-02", "lat": 28.6300, "lon": 77.1950, "available": True},
            {"id": "AMB-03", "lat": 28.5800, "lon": 77.2400, "available": True},
            {"id": "AMB-04", "lat": 28.6500, "lon": 77.2600, "available": True},
        ],
        "fire_truck": [
            {"id": "FT-01", "lat": 28.6200, "lon": 77.2200, "available": True},
            {"id": "FT-02", "lat": 28.6000, "lon": 77.1800, "available": True},
        ],
        "boat": [
            {"id": "BOAT-01", "lat": 28.6100, "lon": 77.2350, "available": True},
            {"id": "BOAT-02", "lat": 28.6350, "lon": 77.2450, "available": True},
            {"id": "BOAT-03", "lat": 28.5950, "lon": 77.2050, "available": True},
        ],
        "helicopter": [
            {"id": "HELI-01", "lat": 28.6500, "lon": 77.2000, "available": True},
        ],
    },
    "volunteers": [
        {"name": "Aarav Sharma", "skill": "medical", "lat": 28.6150, "lon": 77.2250, "available": True},
        {"name": "Priya Nair", "skill": "medical", "lat": 28.6000, "lon": 77.1900, "available": True},
        {"name": "Rohan Gupta", "skill": "engineer", "lat": 28.6400, "lon": 77.2500, "available": True},
        {"name": "Simran Kaur", "skill": "driver", "lat": 28.5900, "lon": 77.2200, "available": True},
        {"name": "Karan Verma", "skill": "engineer", "lat": 28.6600, "lon": 77.2100, "available": True},
    ],
    "points_of_interest": [
        {"name": "Central Hospital Zone", "type": "hospital", "lat": 28.5672, "lon": 77.2100, "population_weight": 1.0},
        {"name": "Public School Block", "type": "school", "lat": 28.6180, "lon": 77.2280, "population_weight": 0.9},
        {"name": "Residential Sector 5", "type": "residential", "lat": 28.6050, "lon": 77.2200, "population_weight": 0.6},
        {"name": "Old Town Market", "type": "residential", "lat": 28.6250, "lon": 77.1950, "population_weight": 0.5},
        {"name": "Industrial Warehouse Zone", "type": "warehouse", "lat": 28.5850, "lon": 77.2450, "population_weight": 0.2},
    ],
}


def default_state():
    return copy.deepcopy(_DEFAULT_STATE)

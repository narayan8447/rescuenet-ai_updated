import random
import copy
import math
from backend.data.simulated_data import default_state, BASE_LAT, BASE_LON

class SimulationEngine:
    def __init__(self, seed: int = 42, epicenter_lat: float = BASE_LAT, epicenter_lon: float = BASE_LON):
        self.seed = seed
        self.rng = random.Random(self.seed)
        self.tick = 0
        self.epicenter = (epicenter_lat, epicenter_lon)
        
        # Load base static state
        self.state = default_state()
        
        # Initialize dynamic fields not in base state
        self.state["weather"] = {
            "temperature_c": 32.0,
            "precipitation_mm": 0.0,
            "wind_speed_kmh": 5.0,
            "wind_direction": "N"
        }
        self.state["disaster_spread_radius_km"] = 0.0
        self.state["traffic_congestion_index"] = 1.0 # 1.0 = normal, higher = worse
        
        # Add baseline damage attributes to POIs
        for poi in self.state["points_of_interest"]:
            poi["damage_level"] = "none" # none, minor, severe, destroyed
            poi["flooded"] = False
            poi["fire"] = False
            
    def get_state(self) -> dict:
        return copy.deepcopy(self.state)
        
    def step(self, ticks: int = 1):
        """Advances the simulation deterministically by N ticks (representing hours)."""
        for _ in range(ticks):
            self.tick += 1
            self._update_weather()
            self._update_spread()
            self._update_damage_and_population()
            self._update_hospitals()
            self._update_traffic()
            self._update_resources()
            
    def _update_weather(self):
        # Random walk for weather based on seeded RNG
        self.state["weather"]["temperature_c"] += self.rng.uniform(-1.0, 1.0)
        self.state["weather"]["precipitation_mm"] = max(0.0, self.state["weather"]["precipitation_mm"] + self.rng.uniform(-5.0, 10.0))
        self.state["weather"]["wind_speed_kmh"] = max(0.0, self.state["weather"]["wind_speed_kmh"] + self.rng.uniform(-2.0, 5.0))
        
        directions = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]
        if self.rng.random() > 0.8:
            self.state["weather"]["wind_direction"] = self.rng.choice(directions)
            
    def _haversine_distance(self, lat1, lon1, lat2, lon2):
        # Rough distance in km
        R = 6371
        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lon2 - lon1)
        a = math.sin(dlat/2) * math.sin(dlat/2) + math.cos(math.radians(lat1)) \
            * math.cos(math.radians(lat2)) * math.sin(dlon/2) * math.sin(dlon/2)
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        return R * c
        
    def _update_spread(self):
        # Disaster radius expands by 0.5km to 1.5km per tick
        expansion_rate = self.rng.uniform(0.5, 1.5)
        self.state["disaster_spread_radius_km"] += expansion_rate
        
        # Check POIs inside radius
        radius = self.state["disaster_spread_radius_km"]
        for poi in self.state["points_of_interest"]:
            dist = self._haversine_distance(self.epicenter[0], self.epicenter[1], poi["lat"], poi["lon"])
            if dist <= radius:
                # If precipitation is high, it's a flood; if temp/wind high, it's a fire.
                if self.state["weather"]["precipitation_mm"] > 10.0:
                    poi["flooded"] = True
                elif self.state["weather"]["temperature_c"] > 35.0 and self.state["weather"]["wind_speed_kmh"] > 15.0:
                    poi["fire"] = True

    def _update_damage_and_population(self):
        for poi in self.state["points_of_interest"]:
            if poi["flooded"] or poi["fire"]:
                # Damage escalates over time if exposed
                if poi["damage_level"] == "none":
                    poi["damage_level"] = "minor"
                elif poi["damage_level"] == "minor" and self.rng.random() > 0.5:
                    poi["damage_level"] = "severe"
                elif poi["damage_level"] == "severe" and self.rng.random() > 0.7:
                    poi["damage_level"] = "destroyed"
                    
                # Population flees to shelters if severe
                if poi["damage_level"] in ["severe", "destroyed"]:
                    fleeing_people = int(poi.get("population_weight", 1.0) * self.rng.randint(10, 50))
                    # Move to random shelter
                    available_shelters = self.state["shelters"]
                    if available_shelters:
                        target = self.rng.choice(available_shelters)
                        target["capacity"] = max(0, target["capacity"] - fleeing_people)
                        # We don't track current occupancy strictly yet, just reducing capacity to simulate crowding
                        
    def _update_hospitals(self):
        # Hospital beds fill up based on disaster radius (casualties arrive)
        casualty_rate = int(self.state["disaster_spread_radius_km"] * self.rng.uniform(1, 5))
        for _ in range(casualty_rate):
            hospitals = self.state["hospitals"]
            if hospitals:
                h = self.rng.choice(hospitals)
                if h["general_beds"] > 0:
                    h["general_beds"] -= 1
                elif h["icu_beds"] > 0:
                    h["icu_beds"] -= 1
                elif h["ventilators"] > 0:
                    h["ventilators"] -= 1

    def _update_traffic(self):
        # Traffic gets worse as radius expands and damage increases
        self.state["traffic_congestion_index"] = 1.0 + (self.state["disaster_spread_radius_km"] * 0.1)
        
    def _update_resources(self):
        # 10% chance per tick for an available resource to become busy
        for res_type, units in self.state["resources"].items():
            for unit in units:
                if unit["available"] and self.rng.random() < 0.1:
                    unit["available"] = False

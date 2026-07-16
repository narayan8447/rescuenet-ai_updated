"""
Agent 5 - Route Optimization Agent

Purpose: turn a raw distance into a "safe route" plan by checking whether
the destination area's roads are blocked/partially blocked (from the Damage
Assessment Agent) and flagging a reroute/delay accordingly. A full system
would run A*/Dijkstra/RL routing over a real road graph (OSM/Google Maps);
here we simulate the *decision logic* that would sit on top of that graph.
"""
from typing import List
from backend.models.schemas import ResourceAssignment, DamageReport, RouteInfo, PriorityItem
from backend.utils import haversine_km


def _road_status_for(target_name: str, priorities: List[PriorityItem], damage_reports: List[DamageReport]) -> str:
    poi = next((p for p in priorities if p.entity == target_name), None)
    if not poi:
        return "open"
    nearest = min(damage_reports, key=lambda d: haversine_km(poi.lat, poi.lon, d.lat, d.lon))
    return nearest.road_status


def plan_routes(assignments: List[ResourceAssignment], priorities: List[PriorityItem], damage_reports: List[DamageReport]) -> List[RouteInfo]:
    routes = []
    for a in assignments:
        road_status = _road_status_for(a.assigned_to, priorities, damage_reports)

        if road_status == "blocked":
            status, note, penalty = "rerouted", "Direct road blocked - alternate route added ~40% distance", 1.4
        elif road_status == "partially_blocked":
            status, note, penalty = "delayed", "Partial obstruction - proceeding with caution, +15% time", 1.15
        else:
            status, note, penalty = "clear", "Direct route, no obstructions detected", 1.0

        routes.append(
            RouteInfo(
                resource_id=a.resource_id,
                destination=a.assigned_to,
                distance_km=round(a.distance_km * penalty, 2),
                status=status,
                note=note,
            )
        )
    return routes

"""
Agent 6 - Hospital Capacity Agent

Purpose: track ICU/general beds and assign incoming casualties to the
nearest hospital with capacity, spilling over to the next nearest hospital
once one fills up. Mutates the shared `hospitals` state (beds go down as
patients are assigned), mirroring a live hospital bed-management feed.
"""
from typing import List
from backend.models.schemas import DamageReport, HospitalAssignment
from backend.utils import haversine_km


def assign_patients(damage_reports: List[DamageReport], hospitals: list) -> List[HospitalAssignment]:
    total_casualties = sum(d.estimated_casualties for d in damage_reports)
    # Assume a portion need urgent hospital admission; rest are treated on-site / at shelters
    incoming = max(1, round(total_casualties * 0.4))

    epicentre_lat = sum(d.lat for d in damage_reports) / len(damage_reports)
    epicentre_lon = sum(d.lon for d in damage_reports) / len(damage_reports)

    ranked = sorted(hospitals, key=lambda h: haversine_km(epicentre_lat, epicentre_lon, h["lat"], h["lon"]))

    assignments = []
    remaining = incoming
    for h in ranked:
        if remaining <= 0:
            break
        capacity = h["icu_beds"] + h["general_beds"]
        take = min(remaining, capacity)
        if take <= 0:
            status = "full - diverting patients"
            assignments.append(HospitalAssignment(hospital_name=h["name"], patients_assigned=0,
                                                    icu_beds_left=h["icu_beds"], general_beds_left=h["general_beds"],
                                                    status=status))
            continue

        icu_take = min(take, h["icu_beds"])
        general_take = take - icu_take
        h["icu_beds"] -= icu_take
        h["general_beds"] -= general_take
        remaining -= take

        status = "accepting patients" if (h["icu_beds"] + h["general_beds"]) > 0 else "now at capacity"
        assignments.append(
            HospitalAssignment(
                hospital_name=h["name"],
                patients_assigned=take,
                icu_beds_left=h["icu_beds"],
                general_beds_left=h["general_beds"],
                status=status,
            )
        )
    return assignments

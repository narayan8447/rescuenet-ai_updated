"""
Agent 6 - Hospital Capacity Agent (Production V2)

Purpose: Tracks ICU/general beds and dynamically assigns incoming casualties 
to the nearest hospital with capacity, using LLMs for distribution logic.
Mutates the shared `hospitals` state (beds go down as patients are assigned).
"""
import os
import time
from typing import List
from tenacity import retry, stop_after_attempt, wait_exponential
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field
from backend.models.schemas import DamageReport, HospitalAssignment
from backend.core.logging import logger
from backend.utils import haversine_km
from backend.core.memory import memory_manager

class HospitalAssignmentList(BaseModel):
    """Wrapper to force LLM to output a list of HospitalAssignments."""
    assignments: List[HospitalAssignment] = Field(description="List of hospital bed assignments.")

# Simulated Tool
def fetch_live_hospital_status(hospital_name: str) -> dict:
    """Mock tool to simulate checking real-time bed telemetry and oxygen supply."""
    logger.info("tool_execution", tool="fetch_live_hospital_status", hospital=hospital_name)
    return {"oxygen_supply": "adequate", "staff_status": "overwhelmed"}

class HospitalCapacityAgentV2:
    def __init__(self):
        self.llm = ChatGroq(
            model="llama-3.1-8b-instant",
            api_key=os.environ.get("GROQ_API_KEY", "dummy_key"),
            max_retries=2
        )
        
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def assign_patients(self, damage_reports: List[DamageReport], hospitals: list) -> List[HospitalAssignment]:
        logger.info("hospital_capacity_started", num_reports=len(damage_reports), num_hospitals=len(hospitals))
        logger.metric("agent_start", 1.0, tags={"agent": "hospital_capacity"})
        
        if not hospitals or not damage_reports:
            return []
            
        if os.environ.get("GROQ_API_KEY", "dummy_key") == "dummy_key":
            logger.warn("using_fallback_hospital_capacity_due_to_missing_groq_key")
            return self._legacy_assign_patients(damage_reports, hospitals)
            
        # Pre-calculations for context
        total_casualties = sum(d.estimated_casualties for d in damage_reports)
        # ~40% require hospital admission
        incoming_patients = max(1, round(total_casualties * 0.4))
        
        epicentre_lat = sum(d.lat for d in damage_reports) / len(damage_reports)
        epicentre_lon = sum(d.lon for d in damage_reports) / len(damage_reports)
        
        # We sort hospitals by proximity to epicentre to help the LLM
        ranked_hospitals = sorted(hospitals, key=lambda h: haversine_km(epicentre_lat, epicentre_lon, h["lat"], h["lon"]))
        
        # Simulate tool usage for the top hospital
        if ranked_hospitals:
            fetch_live_hospital_status(ranked_hospitals[0]["name"])
            
        prompt = ChatPromptTemplate.from_messages([
            ("system", "You are an AI medical dispatcher. We have {incoming} critical patients that need immediate admission. Distribute them across the provided list of hospitals. Fill the nearest (first in list) hospitals first. Consume ICU beds before general beds. Never exceed a hospital's capacity. If patients remain after filling all hospitals, the remaining are unassigned. Provide a list of assignments."),
            ("human", "Incoming Patients: {incoming}\nHospitals (Ordered by proximity): {hospitals}")
        ])
        
        structured_llm = self.llm.with_structured_output(HospitalAssignmentList)
        chain = prompt | structured_llm
        
        try:
            result: HospitalAssignmentList = chain.invoke({
                "incoming": incoming_patients,
                "hospitals": ranked_hospitals
            })
            
            assignments = result.assignments
            
            # Post-Process: The LLM suggests assignments, but we MUST securely mutate the actual state.
            # We recalculate the deductions to prevent hallucination over-booking.
            final_assignments = []
            
            while not memory_manager.acquire_lock("live_state_hospitals", timeout=10):
                time.sleep(0.1)
                
            try:
                remaining = incoming_patients
                total_admitted = 0
                
                for h in ranked_hospitals:
                    # Find what the LLM suggested for this hospital
                    llm_assign = next((a for a in assignments if a.hospital_name == h["name"]), None)
                    if not llm_assign:
                        continue
                        
                    if remaining <= 0:
                        break
                        
                    capacity = h["icu_beds"] + h["general_beds"]
                    # Take min of what's remaining, what the LLM suggested, and the actual physical capacity
                    take = min(remaining, llm_assign.patients_assigned, capacity)
                    
                    if take <= 0:
                        status = "full - diverting patients"
                        final_assignments.append(HospitalAssignment(
                            hospital_name=h["name"], patients_assigned=0,
                            icu_beds_left=h["icu_beds"], general_beds_left=h["general_beds"],
                            status=status))
                        continue

                    icu_take = min(take, h["icu_beds"])
                    general_take = take - icu_take
                    
                    # Mutate the global state dict so other agents see reduced capacity
                    h["icu_beds"] -= icu_take
                    h["general_beds"] -= general_take
                    remaining -= take
                    total_admitted += take

                    status = "accepting patients" if (h["icu_beds"] + h["general_beds"]) > 0 else "now at capacity"
                    final_assignments.append(
                        HospitalAssignment(
                            hospital_name=h["name"],
                            patients_assigned=take,
                            icu_beds_left=h["icu_beds"],
                            general_beds_left=h["general_beds"],
                            status=status,
                        )
                    )
            finally:
                memory_manager.release_lock("live_state_hospitals")
                
            # Log metrics
            logger.info("hospital_capacity_success", total_admitted=total_admitted, overflow=remaining)
            logger.metric("patients_admitted", float(total_admitted), tags={"agent": "hospital_capacity"})
            if remaining > 0:
                logger.metric("patients_unadmitted_overflow", float(remaining), tags={"agent": "hospital_capacity"})
                
            return final_assignments
            
        except Exception as e:
            logger.error("hospital_capacity_failed", error=str(e))
            raise e
            
    def _legacy_assign_patients(self, damage_reports: List[DamageReport], hospitals: list) -> List[HospitalAssignment]:
        total_casualties = sum(d.estimated_casualties for d in damage_reports)
        incoming = max(1, round(total_casualties * 0.4))

        epicentre_lat = sum(d.lat for d in damage_reports) / len(damage_reports)
        epicentre_lon = sum(d.lon for d in damage_reports) / len(damage_reports)

        ranked = sorted(hospitals, key=lambda h: haversine_km(epicentre_lat, epicentre_lon, h['lat'], h['lon']))

        assignments = []
        while not memory_manager.acquire_lock('live_state_hospitals', timeout=10):
            time.sleep(0.1)
        try:
            remaining = incoming
            for h in ranked:
                if remaining <= 0:
                    break
                capacity = h['icu_beds'] + h['general_beds']
                take = min(remaining, capacity)
                if take <= 0:
                    status = 'full - diverting patients'
                    assignments.append(HospitalAssignment(hospital_name=h['name'], patients_assigned=0,
                                                            icu_beds_left=h['icu_beds'], general_beds_left=h['general_beds'],
                                                            status=status))
                    continue

                icu_take = min(take, h['icu_beds'])
                general_take = take - icu_take
                h['icu_beds'] -= icu_take
                h['general_beds'] -= general_take
                remaining -= take

                status = 'accepting patients' if (h['icu_beds'] + h['general_beds']) > 0 else 'now at capacity'
                assignments.append(
                    HospitalAssignment(
                        hospital_name=h['name'],
                        patients_assigned=take,
                        icu_beds_left=h['icu_beds'],
                        general_beds_left=h['general_beds'],
                        status=status,
                    )
                )
        finally:
            memory_manager.release_lock('live_state_hospitals')
        return assignments

_agent = HospitalCapacityAgentV2()

def assign_patients(damage_reports: List[DamageReport], hospitals: list) -> List[HospitalAssignment]:
    return _agent.assign_patients(damage_reports, hospitals)

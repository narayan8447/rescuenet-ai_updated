import requests
import json
import os

API_BASE = "http://127.0.0.1:8000"
OUTPUT_DIR = "presentation_outputs"

if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)

def save_json(filename, data):
    filepath = os.path.join(OUTPUT_DIR, filename)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)
    print(f"✅ Saved: {filepath}")

def main():
    print("🚀 Generating sample outputs from local backend...")
    print("Make sure your backend is running on http://127.0.0.1:8000\n")

    # 1. Trigger Disaster (Live Response)
    print("Triggering disaster response pipeline (this may take a few seconds)...")
    trigger_payload = {
        "disaster_type": "earthquake",
        "location_name": "San Francisco",
        "lat": 37.7749,
        "lon": -122.4194
    }
    try:
        resp = requests.post(f"{API_BASE}/api/disaster/trigger", json=trigger_payload, timeout=120)
        if resp.status_code == 200:
            save_json("1_Live_Response_Output.json", resp.json())
        else:
            print(f"❌ Failed to trigger disaster: {resp.status_code} {resp.text}")
    except Exception as e:
        print(f"❌ Error triggering disaster: {e}")

    # 2. Incident History
    print("\nFetching incident history...")
    try:
        resp = requests.get(f"{API_BASE}/api/incidents", timeout=30)
        if resp.status_code == 200:
            save_json("2_Incident_History_Output.json", resp.json())
        else:
            print(f"❌ Failed to fetch history: {resp.status_code}")
    except Exception as e:
        print(f"❌ Error fetching history: {e}")

    # 3. Live Resource State
    print("\nFetching live resource state...")
    try:
        resp = requests.get(f"{API_BASE}/api/state", timeout=30)
        if resp.status_code == 200:
            save_json("3_Live_Resource_State_Output.json", resp.json())
        else:
            print(f"❌ Failed to fetch state: {resp.status_code}")
    except Exception as e:
        print(f"❌ Error fetching state: {e}")

    # 4. RAG Knowledge Base
    print("\nQuerying RAG Knowledge Base...")
    rag_payload = {
        "query": "What are the standard evacuation protocols for an earthquake?"
    }
    try:
        resp = requests.post(f"{API_BASE}/api/rag/search", json=rag_payload, timeout=60)
        if resp.status_code == 200:
            save_json("4_RAG_Knowledge_Base_Output.json", resp.json())
        else:
            print(f"❌ Failed to query RAG: {resp.status_code}")
    except Exception as e:
        print(f"❌ Error querying RAG: {e}")

    print(f"\n🎉 All done! You can now open the '{OUTPUT_DIR}' folder in your editor and take screenshots of the clean JSON outputs.")

if __name__ == "__main__":
    main()

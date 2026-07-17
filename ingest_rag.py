import urllib.request
import json

url = 'http://127.0.0.1:8000/api/rag/ingest'
headers = {'Content-Type': 'application/json'}
data = [
    {"text": "Flood Evacuation: Move to higher ground immediately. Do not walk through moving water. Six inches of moving water can make you fall. If you must walk in water, walk where the water is not moving. Use a stick to check the firmness of the ground in front of you. Do not drive into flooded areas. If floodwaters rise around your car, abandon the car and move to higher ground if you can do so safely.", "metadata": {"source": "FEMA Flood Protocol", "type": "guideline"}},
    {"text": "Earthquake Response: Drop, Cover, and Hold On! Drop to your hands and knees. Cover your head and neck with your arms. If a sturdy table or desk is nearby, crawl underneath it for shelter. If no shelter is nearby, crawl next to an interior wall (away from windows). Hold on to any sturdy covering so you can move with it until the shaking stops.", "metadata": {"source": "Red Cross Earthquake Guide", "type": "guideline"}},
    {"text": "Wildfire Protocols: Evacuate immediately if instructed to do so. If trapped, call 911. Turn on lights to increase visibility. Close all doors and windows but do not lock them. Fill sinks and tubs with cold water. Keep your emergency supply kit ready. If outdoors, look for a body of water or cleared area. Lie flat and cover your body with wet clothing or soil.", "metadata": {"source": "National Fire Protection Association", "type": "guideline"}}
]

try:
    req = urllib.request.Request(url, data=json.dumps(data).encode(), headers=headers)
    with urllib.request.urlopen(req) as response:
        print(response.read().decode())
except Exception as e:
    print(e)

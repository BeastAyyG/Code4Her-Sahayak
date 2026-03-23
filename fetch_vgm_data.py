import requests
import json

# overpass bbox format: south,west,north,east
BBOX = "16.20,80.30,16.60,80.75"

query = f"""
[out:json][timeout:50];
(
  way["lit"="yes"]({BBOX});
  way["highway"~"primary|secondary|trunk"]({BBOX});
);
out body;
>;
out skel qt;
"""

print("Running query...")
response = requests.post("https://overpass-api.de/api/interpreter", data={"data": query})

if response.status_size == 200 or response.status_code == 200:
    data = response.json()
    with open("vgm_streets.json", "w") as f:
        json.dump(data, f)
    print(f"Saved {len(data.get('elements', []))} elements to vgm_streets.json.")
else:
    print(f"Error {response.status_code}: {response.text}")

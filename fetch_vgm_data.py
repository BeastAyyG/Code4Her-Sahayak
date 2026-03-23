#!/usr/bin/env python3
"""
Fetch real VGM public data from OpenStreetMap via Overpass and convert it
into local JSON files that the app can consume directly.

Outputs:
- vgm_streets.json  (GeoJSON FeatureCollection of streets)
- vgm_havens.json   (GeoJSON FeatureCollection of active civic places)
"""

from __future__ import annotations

import json
import math
import sys
import time
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parent
OVERPASS_URL = "https://overpass-api.de/api/interpreter"
BBOX = "16.20,80.30,16.60,80.75"  # south,west,north,east
USER_AGENT = "code4her-sahayak/1.0 (+https://github.com/)"


def post_overpass(query: str) -> Dict[str, Any]:
    payload = urlencode({"data": query}).encode("utf-8")
    request = Request(
        OVERPASS_URL,
        data=payload,
        headers={
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            "User-Agent": USER_AGENT,
        },
        method="POST",
    )
    with urlopen(request, timeout=180) as response:
        return json.loads(response.read().decode("utf-8"))


def build_index(elements: Iterable[Dict[str, Any]]) -> Tuple[Dict[int, Dict[str, Any]], Dict[int, Dict[str, Any]], Dict[int, Dict[str, Any]]]:
    nodes: Dict[int, Dict[str, Any]] = {}
    ways: Dict[int, Dict[str, Any]] = {}
    relations: Dict[int, Dict[str, Any]] = {}
    for element in elements:
        element_type = element.get("type")
        element_id = element.get("id")
        if element_type == "node":
            nodes[element_id] = element
        elif element_type == "way":
            ways[element_id] = element
        elif element_type == "relation":
            relations[element_id] = element
    return nodes, ways, relations


def way_to_linestring(way: Dict[str, Any], node_index: Dict[int, Dict[str, Any]]) -> List[List[float]] | None:
    coords: List[List[float]] = []
    for node_id in way.get("nodes", []):
        node = node_index.get(node_id)
        if not node:
            continue
        coords.append([node["lon"], node["lat"]])
    return coords if len(coords) >= 2 else None


def infer_lighting(tags: Dict[str, str]) -> str:
    if tags.get("lit") == "yes":
        return "yes"
    if tags.get("lit") == "no":
        return "no"
    if tags.get("highway") in {"trunk", "primary", "secondary", "tertiary"}:
        return "assumed_yes"
    return "unknown"


def street_features(elements: List[Dict[str, Any]]) -> Dict[str, Any]:
    nodes, ways, _ = build_index(elements)
    features: List[Dict[str, Any]] = []

    for way in ways.values():
        tags = way.get("tags", {})
        highway = tags.get("highway")
        if highway not in {"trunk", "primary", "secondary", "tertiary", "residential", "service", "unclassified"} and tags.get("lit") not in {"yes", "no"}:
            continue

        coords = way_to_linestring(way, nodes)
        if not coords:
            continue

        features.append(
            {
                "type": "Feature",
                "properties": {
                    "osm_id": way["id"],
                    "name": tags.get("name") or tags.get("ref") or "Unnamed Street",
                    "highway": highway or "unknown",
                    "lit": infer_lighting(tags),
                    "surface": tags.get("surface"),
                    "lanes": tags.get("lanes"),
                },
                "geometry": {
                    "type": "LineString",
                    "coordinates": coords,
                },
            }
        )

    return {"type": "FeatureCollection", "features": features}


def amenity_icon(feature_type: str) -> str:
    return {
        "police": "shield-check",
        "hospital": "hospital",
        "pharmacy": "pill",
        "clinic": "stethoscope",
        "fire_station": "flame",
        "fuel": "fuel",
        "convenience": "store",
        "atm": "credit-card",
        "bus_station": "bus",
        "railway_station": "train-track",
    }.get(feature_type, "map-pin")


def haven_type(tags: Dict[str, str]) -> str:
    if tags.get("amenity"):
        return tags["amenity"]
    if tags.get("shop") == "convenience":
        return "convenience"
    if tags.get("railway") == "station":
        return "railway_station"
    return "active_area"


def haven_name(tags: Dict[str, str], fallback: str) -> str:
    return tags.get("name") or tags.get("operator") or tags.get("brand") or fallback


def point_from_element(element: Dict[str, Any], node_index: Dict[int, Dict[str, Any]]) -> List[float] | None:
    if element["type"] == "node":
        return [element["lon"], element["lat"]]
    center = element.get("center")
    if center:
        return [center["lon"], center["lat"]]

    if element["type"] == "way":
        coords = way_to_linestring(element, node_index)
        if not coords:
            return None
        lon = sum(point[0] for point in coords) / len(coords)
        lat = sum(point[1] for point in coords) / len(coords)
        return [lon, lat]

    return None


def haven_features(elements: List[Dict[str, Any]]) -> Dict[str, Any]:
    nodes, ways, relations = build_index(elements)
    features: List[Dict[str, Any]] = []

    source_elements = list(nodes.values()) + list(ways.values()) + list(relations.values())
    for element in source_elements:
        tags = element.get("tags", {})
        feature_type = haven_type(tags)
        if feature_type == "active_area":
            continue

        point = point_from_element(element, nodes)
        if not point:
            continue

        features.append(
            {
                "type": "Feature",
                "properties": {
                    "osm_id": element["id"],
                    "name": haven_name(tags, feature_type.replace("_", " ").title()),
                    "type": feature_type,
                    "icon": amenity_icon(feature_type),
                    "open": tags.get("opening_hours") or ("24/7" if feature_type in {"police", "hospital", "fire_station", "fuel"} else "Unknown"),
                },
                "geometry": {
                    "type": "Point",
                    "coordinates": point,
                },
            }
        )

    return {"type": "FeatureCollection", "features": features}


def write_json(path: Path, data: Dict[str, Any]) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")


def main() -> int:
    streets_query = f"""
[out:json][timeout:120];
(
  way["lit"="yes"]({BBOX});
  way["lit"="no"]({BBOX});
  way["highway"~"trunk|primary|secondary|tertiary"]({BBOX});
);
(._;>;);
out body;
"""

    havens_query = f"""
[out:json][timeout:120];
(
  node["amenity"~"police|hospital|pharmacy|clinic|fire_station|fuel|atm|bus_station"]({BBOX});
  way["amenity"~"police|hospital|pharmacy|clinic|fire_station|fuel|atm|bus_station"]({BBOX});
  relation["amenity"~"police|hospital|pharmacy|clinic|fire_station|fuel|atm|bus_station"]({BBOX});
  node["shop"="convenience"]({BBOX});
  way["shop"="convenience"]({BBOX});
  relation["shop"="convenience"]({BBOX});
  node["railway"="station"]({BBOX});
  way["railway"="station"]({BBOX});
  relation["railway"="station"]({BBOX});
);
out center;
"""

    print("Fetching VGM streets from Overpass...")
    streets_raw = post_overpass(streets_query)
    streets_geojson = street_features(streets_raw.get("elements", []))
    streets_path = ROOT / "vgm_streets.json"
    write_json(streets_path, streets_geojson)
    print(f"Wrote {len(streets_geojson['features'])} street features to {streets_path.name}")

    time.sleep(2)

    print("Fetching VGM active places from Overpass...")
    havens_raw = post_overpass(havens_query)
    havens_geojson = haven_features(havens_raw.get("elements", []))
    havens_path = ROOT / "vgm_havens.json"
    write_json(havens_path, havens_geojson)
    print(f"Wrote {len(havens_geojson['features'])} active places to {havens_path.name}")

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (HTTPError, URLError) as exc:
        print(f"Overpass request failed: {exc}", file=sys.stderr)
        raise SystemExit(1)

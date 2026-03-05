"""
Open data fetching utilities using OpenStreetMap (via osmnx) and OpenChargeMap.

This module provides a single entrypoint `fetch_city_data` which returns:
 - road networkx graph (drive network)
 - amenities GeoDataFrame (POIs)
 - existing EV charging stations from OpenChargeMap
 - candidate site points (derived from road nodes + amenities)
"""

from __future__ import annotations

import random
import time
from typing import Dict, Tuple

import geopandas as gpd
import networkx as nx
import osmnx as ox
import pandas as pd
import requests
from shapely.geometry import Point

from utils.config import DEFAULT_MAX_CANDIDATES
from utils.helpers import setup_logger


OCCM_ENDPOINT = "https://api.openchargemap.io/v3/poi/"


def _fetch_road_graph(place: str) -> nx.MultiDiGraph:
    return ox.graph_from_place(place, network_type="drive", simplify=True)


def _fetch_amenities(place: str) -> gpd.GeoDataFrame:
    tags = {
        "amenity": True,
        "shop": True,
        "landuse": ["retail", "commercial"],
    }
    g = ox.geometries_from_place(place, tags)
    # Ensure points by taking centroids for polygons/lines (use projected CRS first)
    g = g.to_crs(3857)
    g["geometry"] = g["geometry"].centroid
    g = g.to_crs(epsg=4326)
    g = g[g.geometry.type == "Point"].copy()
    g["poi_type"] = g["amenity"].fillna(g["shop"]).fillna(g["landuse"]).fillna("poi")
    return g[["poi_type", "geometry"]].reset_index(drop=True)


def _fetch_openchargemap(place_bounds: gpd.GeoSeries, max_results: int = 500) -> gpd.GeoDataFrame:
    bbox = place_bounds.total_bounds  # minx, miny, maxx, maxy
    min_lon, min_lat, max_lon, max_lat = bbox[0], bbox[1], bbox[2], bbox[3]
    params = {
        "output": "json",
        "maxresults": max_results,
        "compact": True,
        "verbose": False,
        "boundingbox": f"{min_lat},{min_lon},{max_lat},{max_lon}",
    }
    # Public API: avoid API key by staying modest in result size and rate
    resp = requests.get(OCCM_ENDPOINT, params=params, timeout=30)
    if resp.status_code == 403:
        # Public API may block anonymous calls; return empty quietly
        return gpd.GeoDataFrame(columns=["name", "geometry"], geometry="geometry", crs="EPSG:4326")
    resp.raise_for_status()
    data = resp.json()
    rows = []
    for item in data:
        addr = item.get("AddressInfo", {})
        lat = addr.get("Latitude")
        lon = addr.get("Longitude")
        if lat is None or lon is None:
            continue
        title = addr.get("Title", "EVCS")
        rows.append({"name": title, "lat": lat, "lon": lon})
    if not rows:
        return gpd.GeoDataFrame(columns=["name", "geometry"], geometry="geometry", crs="EPSG:4326")
    df = pd.DataFrame(rows)
    gdf = gpd.GeoDataFrame(df, geometry=gpd.points_from_xy(df["lon"], df["lat"]), crs="EPSG:4326")
    return gdf[["name", "geometry"]]


def _make_candidate_sites(G: nx.MultiDiGraph, pois: gpd.GeoDataFrame, limit: int) -> gpd.GeoDataFrame:
    nodes, _ = ox.graph_to_gdfs(G)
    nodes = nodes.sample(min(len(nodes), limit), random_state=0)
    poi_pts = pois.sample(min(len(pois), max(1, limit // 2)), random_state=0)
    combined = pd.concat([
        gpd.GeoDataFrame(nodes[["geometry"]]).assign(source="road_node"),
        gpd.GeoDataFrame(poi_pts[["geometry"]]).assign(source="poi"),
    ], ignore_index=True)
    combined = combined.to_crs(epsg=4326)
    combined["cand_id"] = [f"C{i:05d}" for i in range(len(combined))]
    return combined[["cand_id", "source", "geometry"]]


def fetch_city_data(city: str, max_candidates: int | None = None) -> Tuple[nx.MultiDiGraph, gpd.GeoDataFrame, gpd.GeoDataFrame, gpd.GeoDataFrame]:
    """Fetch road graph, POIs, existing EVCS, and candidate sites for a city.

    Parameters
    ----------
    city: str
        City/place string compatible with OSMnx (e.g., "Hefei, Anhui, China").
    max_candidates: Optional[int]
        Upper bound on number of candidate locations generated.

    Returns
    -------
    (graph, pois, existing_evcs, candidates)
    """
    logger = setup_logger()
    logger.info(f"Fetching OSM road graph for: {city}")
    G = _fetch_road_graph(city)

    logger.info("Fetching amenities/POIs from OSM")
    pois = _fetch_amenities(city)

    logger.info("Fetching existing EVCS from OpenChargeMap")
    place_shape = ox.geocode_to_gdf(city).to_crs(epsg=4326)
    existing = _fetch_openchargemap(place_shape.geometry)

    limit = max_candidates or DEFAULT_MAX_CANDIDATES
    logger.info(f"Generating up to {limit} candidate sites")
    candidates = _make_candidate_sites(G, pois, limit)

    # Be gentle to public services
    time.sleep(1.0)
    return G, pois, existing, candidates


__all__ = ["fetch_city_data"]




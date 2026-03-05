"""
Helper utilities for the EVCS hybrid optimization project.
Includes logging setup, geospatial helpers, and simple IO utilities.
"""

from __future__ import annotations

import json
import logging
import math
from pathlib import Path
from typing import Any, Iterable, Tuple

import geopandas as gpd
from shapely.geometry import Point


def setup_logger(name: str = "evcs") -> logging.Logger:
    """Create and configure a console logger.

    Parameters
    ----------
    name: str
        Logger name.

    Returns
    -------
    logging.Logger
        Configured logger instance.
    """
    logger = logging.getLogger(name)
    if not logger.handlers:
        logger.setLevel(logging.INFO)
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            fmt="%(asctime)s | %(levelname)s | %(message)s",
            datefmt="%H:%M:%S",
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    return logger


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Compute the Haversine distance between two points in kilometers."""
    R = 6371.0
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c


def ensure_outputs_dir(path: str | Path) -> Path:
    """Ensure outputs directory exists."""
    p = Path(path)
    p.mkdir(parents=True, exist_ok=True)
    return p


def save_geojson(gdf: gpd.GeoDataFrame, path: str | Path) -> None:
    """Save a GeoDataFrame to GeoJSON with UTF-8 encoding."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    # Use driver GeoJSON for robust output
    gdf.to_file(path, driver="GeoJSON")


def to_point(lat: float, lon: float) -> Point:
    return Point(lon, lat)


def write_json(obj: Any, path: str | Path) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)


def pairwise(iterable: Iterable[Any]) -> Iterable[Tuple[Any, Any]]:
    items = list(iterable)
    for i in range(len(items)):
        for j in range(i + 1, len(items)):
            yield items[i], items[j]


__all__ = [
    "setup_logger",
    "haversine_km",
    "ensure_outputs_dir",
    "save_geojson",
    "to_point",
    "write_json",
    "pairwise",
]




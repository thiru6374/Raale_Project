"""
src/utils/map_utils.py

Plotly version-aware map utility for geographic scatter plots.

Plotly 6.0+ removed `scatter_mapbox`, `line_mapbox`, `density_mapbox`
and `choropleth_mapbox` in favour of:
  - px.scatter_map      (requires Plotly >= 6)
  - px.line_map         (requires Plotly >= 6)
  - px.density_map      (requires Plotly >= 6)
  - px.choropleth_map   (requires Plotly >= 6)

Key parameter renames:
  - mapbox_style  → map_style
  - mapbox_center → (not changed; center is still `center=`)

This module detects the installed Plotly version and always calls the
correct API so that pages never crash due to a version mismatch.

Centralized map preparation (prepare_map_dataframe) normalises column
aliases and validates geo data so both the Main Dashboard and Risk Map
page use identical logic.
"""


# ── Canonical risk-level colour palette ─────────────────────────────────────
RISK_COLOR_MAP = {
    "VERY HIGH": "#dc2626",
    "HIGH":      "#ea580c",
    "MODERATE":  "#ca8a04",
    "LOW":       "#16a34a",
    "VERY LOW":  "#0ea5e9",
    "UNKNOWN":   "#94a3b8",
}

# Canonical display ordering (highest risk first)
RISK_ORDER = ["VERY HIGH", "HIGH", "MODERATE", "LOW", "VERY LOW", "UNKNOWN"]

# Chennai default centre
CHENNAI_CENTER = {"lat": 13.05, "lon": 80.20}


import streamlit as st

@st.cache_data(show_spinner=False, max_entries=5)
def prepare_map_dataframe(df, dataset_signature: str = "") -> "tuple[pd.DataFrame, dict]":
    """
    Prepare a pipeline DataFrame for map rendering.

    Performs:
      - Column alias normalisation (risk_score, risk_level, lat/lon)
      - Coordinate numeric conversion and Chennai-range validation
      - Aggregation to one row per neighbourhood (latest observation)
      - Returns (map_df, info_dict) where info_dict contains diagnostic counts.

    The returned map_df is safe to pass directly to scatter_map().
    Records with invalid coordinates are excluded from map_df only —
    the original df is never modified.

    Parameters
    ----------
    df : pd.DataFrame
        The canonical pipeline result DataFrame from AppState.
    dataset_signature : str
        Cache key derived from dataset metadata to prevent stale cache bugs
        while maintaining high performance for 50k+ row datasets.

    Returns
    -------
    map_df : pd.DataFrame
        De-duplicated, geo-valid DataFrame ready for scatter_map().
    info : dict
        {total_records, valid_geo, invalid_geo, observation_date, centre}
    """
    import numpy as np

    if df is None or df.empty:
        return pd.DataFrame(), {"total_records": 0, "valid_geo": 0, "invalid_geo": 0,
                                "observation_date": "N/A", "centre": CHENNAI_CENTER}

    out = df.copy()

    # ── 1. Risk Score ────────────────────────────────────────────────────────
    for _rs in ("risk_score", "multi_factor_risk_score", "composite_risk_score",
                "temperature_c", "heat_index"):
        if _rs in out.columns:
            out["_map_risk_score"] = pd.to_numeric(out[_rs], errors="coerce").fillna(0.1).clip(lower=0.01)
            break
    else:
        out["_map_risk_score"] = 0.3

    # ── 2. Risk Level ────────────────────────────────────────────────────────
    _LEVEL_ALIASES = {
        "EXTREME": "VERY HIGH", "VERY HIGH": "VERY HIGH",
        "HIGH": "HIGH", "MODERATE": "MODERATE", "MEDIUM": "MODERATE",
        "LOW": "LOW", "VERY LOW": "VERY LOW",
    }
    if "risk_level" in out.columns:
        out["_map_risk_level"] = out["risk_level"].map(
            lambda v: _LEVEL_ALIASES.get(str(v).upper(), "UNKNOWN")
        )
    elif "multi_factor_risk_category" in out.columns:
        out["_map_risk_level"] = out["multi_factor_risk_category"].map(
            lambda v: _LEVEL_ALIASES.get(str(v).upper(), "UNKNOWN")
        )
    else:
        out["_map_risk_level"] = "UNKNOWN"

    # ── 3. Latitude / Longitude ──────────────────────────────────────────────
    lat_col = next((c for c in ("latitude", "lat") if c in out.columns), None)
    lon_col = next((c for c in ("longitude", "lon", "lng") if c in out.columns), None)

    if lat_col:
        out["_map_lat"] = pd.to_numeric(out[lat_col], errors="coerce")
    else:
        out["_map_lat"] = np.nan

    if lon_col:
        out["_map_lon"] = pd.to_numeric(out[lon_col], errors="coerce")
    else:
        out["_map_lon"] = np.nan

    # ── 4. Neighbourhood name ────────────────────────────────────────────────
    if "neighbourhood_name" not in out.columns:
        out["neighbourhood_name"] = out.get("neighbourhood_id", out.index.astype(str))

    # ── 5. Observation date ──────────────────────────────────────────────────
    obs_date = "Latest"
    for _dc in ("observation_date", "date", "timestamp"):
        if _dc in out.columns:
            try:
                dates = pd.to_datetime(out[_dc], errors="coerce").dropna()
                if len(dates):
                    obs_date = str(dates.max().date())
            except Exception:
                pass
            break

    # ── 6. Aggregate to neighbourhood level (one row per neighbourhood_id) ──
    if "neighbourhood_id" in out.columns:
        # Keep first occurrence per neighbourhood (pipeline already filtered to latest date)
        out = out.drop_duplicates(subset=["neighbourhood_id"], keep="first")

    total_records = len(out)

    # ── 7. Geo validation ────────────────────────────────────────────────────
    # Chennai bounding box (with 0.5° tolerance)
    CHENNAI_LAT = (12.4, 13.7)
    CHENNAI_LON = (79.5, 80.8)

    geo_valid = (
        out["_map_lat"].notna()
        & out["_map_lon"].notna()
        & out["_map_lat"].between(*CHENNAI_LAT)
        & out["_map_lon"].between(*CHENNAI_LON)
    )

    invalid_geo = int((~geo_valid).sum())
    valid_geo = int(geo_valid.sum())

    map_df = out[geo_valid].copy()

    # Compute map centre from actual data
    if valid_geo > 0:
        centre = {
            "lat": float(map_df["_map_lat"].mean()),
            "lon": float(map_df["_map_lon"].mean()),
        }
    else:
        centre = CHENNAI_CENTER

    info = {
        "total_records": total_records,
        "valid_geo": valid_geo,
        "invalid_geo": invalid_geo,
        "observation_date": obs_date,
        "centre": centre,
    }

    return map_df, info

import logging
from typing import Any, Dict, List, Optional

import pandas as pd
import plotly.express as px
import plotly

logger = logging.getLogger(__name__)

# ── Version Detection ─────────────────────────────────────────────────────────
_PLOTLY_VERSION = tuple(int(x) for x in plotly.__version__.split(".")[:2])
_HAS_SCATTER_MAP = hasattr(px, "scatter_map")          # Plotly >= 6
_HAS_SCATTER_MAPBOX = hasattr(px, "scatter_mapbox")    # Plotly < 6

# Default map style compatible with both APIs (no token required)
_DEFAULT_STYLE_NEW = "carto-positron"   # value for map_style (Plotly 6+)
_DEFAULT_STYLE_OLD = "carto-positron"   # value for mapbox_style (Plotly < 6)


def scatter_map(
    data_frame: pd.DataFrame,
    lat: str = "latitude",
    lon: str = "longitude",
    color: Optional[str] = None,
    size: Optional[str] = None,
    hover_name: Optional[str] = None,
    hover_data: Optional[Dict[str, Any]] = None,
    color_discrete_map: Optional[Dict[str, str]] = None,
    color_continuous_scale: Optional[Any] = None,
    map_style: str = _DEFAULT_STYLE_NEW,
    center: Optional[Dict[str, float]] = None,
    zoom: float = 10,
    height: int = 600,
    opacity: float = 0.85,
    size_max: int = 20,
    **kwargs,
) -> Any:
    """
    Creates a geographic scatter plot using the best available Plotly API.

    Args:
        data_frame: DataFrame with the data to plot.
        lat: Column name for latitude.
        lon: Column name for longitude.
        color: Column name for color encoding.
        size: Column name for marker size (must be positive numeric).
        hover_name: Column name for the hover title.
        hover_data: Dict of extra hover fields.
        color_discrete_map: Map of category → hex color string.
        color_continuous_scale: Plotly color scale name for continuous color.
        map_style: Background tile style (e.g. 'carto-positron', 'open-street-map').
        center: Dict with 'lat' and 'lon' keys for the map centre.
        zoom: Initial zoom level.
        height: Chart height in pixels.
        opacity: Marker opacity (0–1).
        size_max: Maximum marker size in pixels.
        **kwargs: Extra keyword arguments forwarded to the underlying function.

    Returns:
        A Plotly Figure object ready for `st.plotly_chart(...)`.

    Raises:
        RuntimeError: Only if neither scatter_map nor scatter_mapbox is available.
    """
    common = dict(
        data_frame=data_frame,
        lat=lat,
        lon=lon,
        color=color,
        size=size,
        hover_name=hover_name,
        hover_data=hover_data,
        color_discrete_map=color_discrete_map,
        color_continuous_scale=color_continuous_scale,
        center=center,
        zoom=zoom,
        height=height,
        opacity=opacity,
        size_max=size_max,
        **kwargs,
    )

    if _HAS_SCATTER_MAP:
        # Plotly 6 / 7 — modern API
        logger.debug("Using px.scatter_map (Plotly %s)", plotly.__version__)
        return px.scatter_map(map_style=map_style, **common)

    elif _HAS_SCATTER_MAPBOX:
        # Plotly 5 and below — legacy API
        logger.debug("Using px.scatter_mapbox (Plotly %s)", plotly.__version__)
        return px.scatter_mapbox(mapbox_style=map_style, **common)

    else:
        raise RuntimeError(
            f"No geographic scatter function available in Plotly {plotly.__version__}. "
            "Install plotly >= 5.15.0."
        )


def line_map(
    data_frame: pd.DataFrame,
    lat: str = "latitude",
    lon: str = "longitude",
    color: Optional[str] = None,
    hover_name: Optional[str] = None,
    map_style: str = _DEFAULT_STYLE_NEW,
    center: Optional[Dict[str, float]] = None,
    zoom: float = 10,
    height: int = 500,
    **kwargs,
) -> Any:
    """Creates a geographic line chart using the best available Plotly API."""
    common = dict(
        data_frame=data_frame, lat=lat, lon=lon, color=color,
        hover_name=hover_name, center=center, zoom=zoom, height=height, **kwargs
    )
    if hasattr(px, "line_map"):
        return px.line_map(map_style=map_style, **common)
    elif hasattr(px, "line_mapbox"):
        return px.line_mapbox(mapbox_style=map_style, **common)
    else:
        raise RuntimeError("No geographic line function available in this Plotly version.")


def density_map(
    data_frame: pd.DataFrame,
    lat: str = "latitude",
    lon: str = "longitude",
    z: Optional[str] = None,
    map_style: str = _DEFAULT_STYLE_NEW,
    center: Optional[Dict[str, float]] = None,
    zoom: float = 10,
    height: int = 500,
    **kwargs,
) -> Any:
    """Creates a geographic density/heatmap using the best available Plotly API."""
    common = dict(
        data_frame=data_frame, lat=lat, lon=lon, z=z,
        center=center, zoom=zoom, height=height, **kwargs
    )
    if hasattr(px, "density_map"):
        return px.density_map(map_style=map_style, **common)
    elif hasattr(px, "density_mapbox"):
        return px.density_mapbox(mapbox_style=map_style, **common)
    else:
        raise RuntimeError("No geographic density function available in this Plotly version.")

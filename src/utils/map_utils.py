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
"""

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

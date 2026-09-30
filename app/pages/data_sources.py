"""
app/pages/data_sources.py – Data Intelligence & Source Selection

• Dynamically scans data/raw/ for available CSV files
• Supports switching between SYNTHETIC / MOCK_API / OPEN_DATA / HYBRID / CSV_DATA
• For CSV_DATA: lets user choose any CSV in data/raw/
• Shows active dataset status card with real file metadata
• Shows dataset diagnostics panel
• Uses AppState.switch_dataset() to properly invalidate all stale state
"""
import os
import streamlit as st
from app.components.layout import apply_global_styles, page_header
from app.components.sidebar import render_sidebar

from src.config.settings import settings
from src.services.app_state import AppState
from src.data_providers.csv_provider import list_available_csv_datasets, get_dataset_signature



page_header(" Data Intelligence & Sources", subtitle=None, icon=":material/database:")
st.markdown(
  "Manage the underlying data providers for the application. "
  "Switch between Synthetic, Open Data, Mock API, Hybrid, or a custom CSV dataset. "
  "When the dataset changes, all pipeline results are automatically refreshed."
)

apply_global_styles()
render_sidebar()

AppState.initialize_application()
if AppState.display_error_fallback():
  st.stop()

# ── Active Dataset Status Card ────────────────────────────────────────────────
st.subheader(" Active Dataset")

info = AppState.get_active_dataset_info()
df_full = AppState.get_pipeline_results()

col_a, col_b, col_c, col_d, col_e = st.columns(5)
col_a.metric("Data Mode", settings.data_mode)

dataset_label = info.get("dataset_name") or info.get("active_csv_dataset", "—")
col_b.metric("Dataset File", dataset_label)

row_count = info.get("dataset_rows", 0) or (len(df_full) if df_full is not None else 0)
col_c.metric("Total Rows Loaded", f"{row_count:,}")

if df_full is not None and "neighbourhood_id" in df_full.columns:
  col_d.metric("Unique Neighbourhoods", f"{df_full['neighbourhood_id'].nunique():,}")
else:
  col_d.metric("Unique Neighbourhoods", "—")

col_e.metric("Pipeline Status", " ACTIVE")

st.markdown("---")

# ── Dataset & Mode Selector ───────────────────────────────────────────────────
st.subheader(" Configuration")

with st.form("data_mode_form"):
  col1, col2 = st.columns([2, 1])

  with col1:
    current_mode = settings.data_mode.upper()
    mode_options = ["CSV_DATA", "SYNTHETIC", "MOCK_API", "OPEN_DATA", "HYBRID"]
    try:
      default_mode_idx = mode_options.index(current_mode)
    except ValueError:
      default_mode_idx = 0

    new_mode = st.selectbox(
      "Select Data Mode",
      options=mode_options,
      index=default_mode_idx,
      help=(
        "CSV_DATA: load your own CSV file from data/raw/ | "
        "Synthetic: AI-generated | Mock API: simulated failures | "
        "Open Data: live Open-Meteo API | Hybrid: mixed"
      ),
    )

  with col2:
    st.markdown("<br>", unsafe_allow_html=True)
    submit = st.form_submit_button(" Apply & Reload Data", type="primary")

  # CSV-mode dataset picker — only shown when mode is CSV_DATA
  selected_csv = settings.active_csv_dataset
  if new_mode == "CSV_DATA":
    available_csvs = list_available_csv_datasets()
    if not available_csvs:
      st.warning(
        f"No CSV files found in `{settings.raw_data_dir}/`. "
        "Upload a CSV to that folder and refresh."
      )
    else:
      try:
        csv_default_idx = available_csvs.index(settings.active_csv_dataset)
      except ValueError:
        csv_default_idx = 0

      selected_csv = st.selectbox(
        "Select CSV Dataset",
        options=available_csvs,
        index=csv_default_idx,
        help="These are all CSV files found in data/raw/",
      )

  if submit:
    AppState.switch_dataset(
      new_filename=selected_csv if new_mode == "CSV_DATA" else None,
      new_mode=new_mode,
    )
    st.rerun()

st.markdown("---")

# ── Provider Metadata ─────────────────────────────────────────────────────────
st.subheader(" Current Provider Status")

provider_meta = st.session_state.get("provider_metadata")
if provider_meta:
  pm_col_a, pm_col_b, pm_col_c, pm_col_d = st.columns(4)

  status = provider_meta.get("provider_status", "UNKNOWN")
  status_icon = "" if "ONLINE" in status or "SUCCESS" in status else ("" if "FALLBACK" in status else "")
  pm_col_a.metric("Status", f"{status_icon} {status.replace('_', ' ')}")

  freshness = provider_meta.get("freshness", "FRESH")
  fresh_icon = "" if freshness == "FRESH" else ("" if freshness == "STALE" else "")
  pm_col_b.metric("Freshness", f"{fresh_icon} {freshness}")

  is_live = provider_meta.get("is_live_data", False)
  pm_col_c.metric("Live Data", "Yes " if is_live else "No ")
  pm_col_d.metric("Fallback Activated", "Yes " if provider_meta.get("fallback_activated") else "No ")

  with st.expander("Detailed Provenance & Source Information"):
    st.json(provider_meta)
else:
  st.info("Run the pipeline to fetch data and view provider status.")

st.markdown("---")

# ── Dataset Diagnostics Panel ─────────────────────────────────────────────────
with st.expander(" Dataset Diagnostics", expanded=False):
  if settings.data_mode == "CSV_DATA":
    file_path = os.path.join(settings.raw_data_dir, settings.active_csv_dataset)
    sig = get_dataset_signature(file_path)
    if sig:
      d1, d2, d3 = st.columns(3)
      d1.markdown(f"**Active File:** `{sig.get('filename', '—')}`")
      d2.markdown(f"**File Path:** `{sig.get('file_path', '—')}`")
      d3.markdown(f"**File Size:** `{sig.get('file_size_bytes', 0):,}` bytes")

      d4, d5, d6 = st.columns(3)
      d4.markdown(f"**Last Modified:** `{sig.get('last_modified', '—')}`")
      d5.markdown(f"**Dataset Signature:** `{sig.get('signature', '—')}`")
      d6.markdown(f"**Rows Loaded:** `{row_count:,}`")
    else:
      st.warning(f"File not found at `{file_path}`")

  if df_full is not None:
    col_info1, col_info2 = st.columns(2)
    with col_info1:
      st.markdown(f"**Columns:** `{len(df_full.columns)}`")
      if "observation_date" in df_full.columns:
        st.markdown(f"**Min Date:** `{df_full['observation_date'].min()}`")
        st.markdown(f"**Max Date:** `{df_full['observation_date'].max()}`")
      if "multi_factor_risk_category" in df_full.columns:
        st.markdown("**Risk Levels:**")
        st.dataframe(df_full["multi_factor_risk_category"].value_counts().to_frame(), use_container_width=True)
    with col_info2:
      if "latitude" in df_full.columns and "longitude" in df_full.columns:
        valid_gps = df_full.dropna(subset=["latitude", "longitude"])
        st.markdown(f"**Valid GPS Rows:** `{len(valid_gps):,}`")
        st.markdown(f"**Invalid GPS Rows:** `{len(df_full) - len(valid_gps):,}`")
      st.markdown(f"**Pipeline Duration:** `{st.session_state.get('pipeline_duration_s', 0):.1f}s`")
      st.markdown(f"**Dataset ID (Governance):** `{st.session_state.get('dataset_id', '—')}`")
  else:
    st.info("No pipeline results available yet.")

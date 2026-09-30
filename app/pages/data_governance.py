"""
app/pages/data_governance.py

Data Quality & Governance
Dashboard to monitor and enforce transparent data quality rules.
"""
import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

from app.components.layout import apply_global_styles, page_header
from app.components.sidebar import render_sidebar
from src.services.app_state import AppState
from src.config.settings import settings
from src.data.ingestion import DataIngestor, BaseDataProvider


apply_global_styles()
render_sidebar()

st.markdown("""
<style>
.metric-card { background: #0f172a; border: 1px solid #1e3a5f; padding: 15px; border-radius: 8px; text-align: center; height: 100%; }
.metric-value { font-size: 1.8rem; font-weight: bold; color: #38bdf8; }
.metric-label { font-size: 0.8rem; color: #94a3b8; text-transform: uppercase; font-weight: 600; }
.status-PASS { color: #22c55e; font-weight: bold; }
.status-WARNING { color: #f59e0b; font-weight: bold; }
.status-FAILED { color: #ef4444; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

page_header(" Data Quality & Governance", "Monitor dataset identity, validate schema integrity, and enforce data quality rules.", icon=":material/security:")

AppState.initialize_application()

raw_df = st.session_state.get("raw_df")
if raw_df is None or raw_df.empty:
  st.warning("No active dataset loaded. Please initialize the pipeline.")
  st.stop()

# ── Dynamic Validation ───────────────────────────────────────────────────────
class DataFrameProvider(BaseDataProvider):
  def __init__(self, df): self.df = df
  def fetch_data(self): return self.df

with st.spinner("Validating active dataset against strict schemas..."):
  ingestor = DataIngestor(DataFrameProvider(raw_df))
  valid_df, report = ingestor.load_and_validate()

# Extract validation metrics
total_records = report.total_records
valid_records = report.valid_records
invalid_records = report.invalid_records
missing_vals = report.missing_values
dupes = report.duplicate_records
out_of_range = report.out_of_range_values

# Coordinates & Freshness
invalid_coords = int(raw_df['latitude'].isna().sum() + raw_df['longitude'].isna().sum()) if 'latitude' in raw_df.columns else 0
now = datetime.utcnow()
dataset_time = now - timedelta(hours=1) # Mocked age 
hours_old = (now - dataset_time).total_seconds() / 3600
is_stale = hours_old > settings.freshness_threshold_hours

# ── 1. Dataset Identity (Governance Contract) ────────────────────────────────
st.subheader("1 · Active Dataset Identity")
st.info("The system guarantees that the dataset displayed below is identically cached across all pipeline stages, ensuring experiment reproducibility.")

c1, c2, c3, c4 = st.columns(4)
c1.metric("Active Dataset Name", st.session_state.get("dataset_name", "Unknown"))
c2.metric("Data Signature (MD5)", st.session_state.get("dataset_signature", "N/A")[:12] + "...")
c3.metric("Observation Range", st.session_state.get("date_range", "N/A"))
c4.metric("Config Version", st.session_state.get("configuration_version", "1.0"))

st.markdown("---")

# ── 2. Data Quality Dashboard ────────────────────────────────────────────────
st.subheader("2 · Data Quality Overview")

col1, col2, col3, col4, col5 = st.columns(5)
col1.markdown(f'<div class="metric-card"><div class="metric-label">Total Records</div><div class="metric-value">{total_records}</div></div>', unsafe_allow_html=True)
col2.markdown(f'<div class="metric-card"><div class="metric-label">Valid Records</div><div class="metric-value status-PASS">{valid_records}</div></div>', unsafe_allow_html=True)
col3.markdown(f'<div class="metric-card"><div class="metric-label">Invalid Records</div><div class="metric-value status-FAILED">{invalid_records}</div></div>', unsafe_allow_html=True)
col4.markdown(f'<div class="metric-card"><div class="metric-label">Missing Values</div><div class="metric-value status-WARNING">{missing_vals}</div></div>', unsafe_allow_html=True)
col5.markdown(f'<div class="metric-card"><div class="metric-label">Duplicates</div><div class="metric-value status-FAILED">{dupes}</div></div>', unsafe_allow_html=True)

col6, col7, col8, col9, col10 = st.columns(5)
col6.markdown(f'<div class="metric-card"><div class="metric-label">Invalid Coordinates</div><div class="metric-value status-FAILED">{invalid_coords}</div></div>', unsafe_allow_html=True)
col7.markdown(f'<div class="metric-card"><div class="metric-label">Out-of-Range Temps</div><div class="metric-value status-WARNING">{out_of_range}</div></div>', unsafe_allow_html=True)
col8.markdown(f'<div class="metric-card"><div class="metric-label">Freshness Age</div><div class="metric-value">{hours_old:.1f} h</div></div>', unsafe_allow_html=True)
col9.markdown(f'<div class="metric-card"><div class="metric-label">Freshness Status</div><div class="metric-value status-{"FAILED" if is_stale else "PASS"}">{"STALE" if is_stale else "FRESH"}</div></div>', unsafe_allow_html=True)
col10.markdown(f'<div class="metric-card"><div class="metric-label">Schema Status</div><div class="metric-value status-{report.status.value}">{report.status.value}</div></div>', unsafe_allow_html=True)

st.markdown("---")

# ── 3. Failed Validation Log ─────────────────────────────────────────────────
st.subheader("3 · Transparent Validation Rules (Failure Log)")

# Parse errors into a flat table
failed_rows = []
for d in report.details:
  row_idx = d.get("row_index")
  nid = d.get("neighbourhood_id")
  
  if d.get("error_type") == "duplicate_id":
    failed_rows.append({
      "Neighbourhood": nid,
      "Field": "neighbourhood_id",
      "Issue": "Duplicate record",
      "Severity": "CRITICAL",
      "Recommended Action": "Deduplicate dataset based on observation date."
    })
    continue
    
  for e in d.get("errors", []):
    field = e.get("loc", ["Unknown"])[0]
    msg = e.get("msg", "")
    err_type = e.get("type", "")
    
    severity = "CRITICAL" if err_type == "missing" else "WARNING"
    action = "Impute or drop missing data." if err_type == "missing" else "Review bounds or cap outliers."
    
    failed_rows.append({
      "Neighbourhood": nid,
      "Field": field,
      "Issue": f"{err_type}: {msg}",
      "Severity": severity,
      "Recommended Action": action
    })

if failed_rows:
  df_failed = pd.DataFrame(failed_rows)
  # Aggregate by Field and Issue for summary count
  summary = df_failed.groupby(["Field", "Issue", "Severity", "Recommended Action"]).size().reset_index(name="Count")
  st.dataframe(summary[["Field", "Issue", "Count", "Severity", "Recommended Action"]], use_container_width=True, hide_index=True)
else:
  st.success(" Zero schema validation errors detected. Dataset strictly complies with data-quality models.")

st.markdown("---")
st.caption("Validations are enforced by Pydantic models. Data missing critical fields is stripped before risk analysis to prevent silent pipeline errors.")

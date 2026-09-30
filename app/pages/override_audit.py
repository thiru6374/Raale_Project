"""
app/pages/override_audit.py

Professional Override & Audit Log Page.
Shows immutable record of all manual interventions, system events,
and configuration changes with filters and evidence linkage.
"""
import streamlit as st
import pandas as pd
from datetime import datetime, timezone

from app.components.layout import apply_global_styles, page_header
from app.components.sidebar import render_sidebar
from src.governance.audit_logger import AuditLogger
from src.security.security_service import SecurityService


apply_global_styles()

st.markdown("""
<style>
  .audit-banner {
    background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
    border: 1px solid #334155;
    border-left: 4px solid #f59e0b;
    border-radius: 8px;
    padding: 16px 20px;
    margin-bottom: 20px;
  }
  .status-authorized { color: #22c55e; font-weight: 600; }
  .status-denied   { color: #ef4444; font-weight: 600; }
  .status-pending  { color: #f59e0b; font-weight: 600; }
  .metric-card {
    background: #1e293b;
    border: 1px solid #334155;
    border-radius: 8px;
    padding: 16px;
    text-align: center;
  }
  .metric-card h3 { font-size: 2rem; font-weight: 700; margin: 0; }
  .metric-card p { color: #94a3b8; font-size: 0.85rem; margin: 0; }
  .chain-box {
    background: #0f172a;
    border: 1px solid #334155;
    border-radius: 6px;
    padding: 12px 16px;
    font-family: monospace;
    font-size: 0.85rem;
    margin-top: 8px;
  }
</style>
""", unsafe_allow_html=True)

render_sidebar()
page_header(" Override & Audit Log", "Immutable record of all overrides, system events and governance actions.")

role = SecurityService.render_role_selector(sidebar=True)
st.sidebar.markdown("---")

# ── Load logs ─────────────────────────────────────────────────────────────────
audit_logger = AuditLogger()
raw_logs = audit_logger.read_logs()

if not raw_logs:
  st.info("No audit log entries found. Override actions and system events will appear here once recorded.")
  st.stop()

all_df = pd.DataFrame(raw_logs)

# Normalize optional columns
for col in ["event_id", "action_type", "actor", "role", "neighbourhood_id",
      "original_decision", "new_decision", "reason", "comment",
      "auth_status", "system_confidence", "analysis_id", "details", "timestamp"]:
  if col not in all_df.columns:
    all_df[col] = None

# Parse timestamps
all_df["timestamp"] = pd.to_datetime(all_df["timestamp"], utc=True, errors="coerce")

# ── Sidebar Filters ────────────────────────────────────────────────────────────
st.sidebar.header(" Filters")

action_types = sorted(all_df["action_type"].dropna().unique())
sel_actions = st.sidebar.multiselect("Action Type", options=action_types, default=action_types)

actors = sorted(all_df["actor"].dropna().unique())
sel_actors = st.sidebar.multiselect("Actor", options=actors)

auth_statuses = sorted(all_df["auth_status"].dropna().unique())
sel_auth = st.sidebar.multiselect("Authorization Status", options=auth_statuses, default=auth_statuses)

date_range = st.sidebar.date_input(
  "Date Range",
  value=(all_df["timestamp"].min().date(), all_df["timestamp"].max().date()),
  key="audit_date_range"
)

# Apply filters
filtered_df = all_df.copy()
if sel_actions:
  filtered_df = filtered_df[filtered_df["action_type"].isin(sel_actions)]
if sel_actors:
  filtered_df = filtered_df[filtered_df["actor"].isin(sel_actors)]
if sel_auth:
  filtered_df = filtered_df[filtered_df["auth_status"].isin(sel_auth)]
if len(date_range) == 2:
  start, end = date_range
  filtered_df = filtered_df[
    (filtered_df["timestamp"].dt.date >= start) &
    (filtered_df["timestamp"].dt.date <= end)
  ]

# ── Summary Metrics ────────────────────────────────────────────────────────────
overrides_df = all_df[all_df["action_type"] == "MANUAL_OVERRIDE"]
denied_df  = all_df[all_df["auth_status"] == "DENIED"]
system_df  = all_df[all_df["action_type"] != "MANUAL_OVERRIDE"]

col1, col2, col3, col4 = st.columns(4)
with col1:
  st.markdown(f"""<div class="metric-card">
    <h3>{len(all_df)}</h3><p>Total Audit Events</p></div>""", unsafe_allow_html=True)
with col2:
  st.markdown(f"""<div class="metric-card">
    <h3 style="color:#22c55e">{len(overrides_df)}</h3><p>Manual Overrides</p></div>""", unsafe_allow_html=True)
with col3:
  st.markdown(f"""<div class="metric-card">
    <h3 style="color:#ef4444">{len(denied_df)}</h3><p>Access Denied</p></div>""", unsafe_allow_html=True)
with col4:
  st.markdown(f"""<div class="metric-card">
    <h3 style="color:#f59e0b">{len(system_df)}</h3><p>System Events</p></div>""", unsafe_allow_html=True)

st.markdown("---")

# ── Main Audit Table ───────────────────────────────────────────────────────────
st.subheader(f"Audit Log — {len(filtered_df)} matching events")

if filtered_df.empty:
  st.warning("No events match the selected filters.")
else:
  # Format for display
  display_df = filtered_df.copy()
  display_df["timestamp"] = display_df["timestamp"].dt.strftime("%Y-%m-%d %H:%M:%S UTC")
  display_df["system_confidence"] = display_df["system_confidence"].apply(
    lambda x: f"{float(x):.0%}" if pd.notna(x) else "—"
  )

  def highlight_auth(val):
    if val == "AUTHORIZED": return "color: #22c55e"
    if val == "DENIED":   return "color: #ef4444"
    return ""

  col_order = [c for c in [
    "timestamp", "action_type", "actor", "role", "neighbourhood_id",
    "original_decision", "new_decision", "reason", "comment",
    "auth_status", "system_confidence", "analysis_id", "event_id"
  ] if c in display_df.columns]

  st.dataframe(
    display_df[col_order].reset_index(drop=True),
    use_container_width=True,
    hide_index=True,
  )

st.markdown("---")

# ── Decision Chain Explorer ────────────────────────────────────────────────────
st.subheader(" Decision Chain Explorer")
st.caption("Select a neighbourhood to trace the original → override → final decision chain.")

override_rows = filtered_df[filtered_df["action_type"] == "MANUAL_OVERRIDE"]
if not override_rows.empty:
  n_ids = override_rows["neighbourhood_id"].dropna().unique().tolist()
  selected_n = st.selectbox("Select Neighbourhood", options=n_ids)
  chain_rows = override_rows[override_rows["neighbourhood_id"] == selected_n].sort_values("timestamp")

  for _, row in chain_rows.iterrows():
    auth_color = "#22c55e" if row.get("auth_status") == "AUTHORIZED" else "#ef4444"
    orig = row.get("original_decision")
    new = row.get("new_decision")
    conf = row.get("system_confidence")
    st.markdown(f"""<div class="chain-box">
      <b>Event ID:</b> {row.get('event_id', '—')}<br>
      <b>Timestamp:</b> {row.get('timestamp', '—')}<br>
      <b>Actor:</b> {row.get('actor', '—')} ({row.get('role', '—')})<br>
      <b>Chain:</b>
      <span style="color:#94a3b8">Original: <b>{orig}</b></span>
      → <span style="color:#f59e0b">Override: <b>{new}</b></span>
      → <span style="color:#22c55e">Final: <b>{new}</b></span><br>
      <b>Reason:</b> {row.get('reason', '—')}<br>
      <b>Comment:</b> {row.get('comment', '—') or '—'}<br>
      <b>Authorization:</b> <span style="color:{auth_color}">{row.get('auth_status', '—')}</span><br>
      <b>System Confidence at Override:</b> {f"{float(conf):.0%}" if pd.notna(conf) else "—"}
    </div>""", unsafe_allow_html=True)
    st.markdown("")
else:
  st.info("No override events recorded yet.")

st.markdown("---")

# ── System Events Log ──────────────────────────────────────────────────────────
st.subheader(" System Events")
sys_events = filtered_df[filtered_df["action_type"] != "MANUAL_OVERRIDE"]
if not sys_events.empty:
  st.dataframe(
    sys_events[["timestamp", "action_type", "actor", "details", "event_id"]].reset_index(drop=True),
    use_container_width=True,
    hide_index=True,
  )
else:
  st.info("No system events in the current filter window.")

st.markdown("---")
st.markdown(
  "<small style='color:#475569'>All audit logs are stored immutably at "
  "<code>data/logs/audit.jsonl</code>. "
  "Entries are append-only and are never modified or deleted.</small>",
  unsafe_allow_html=True
)

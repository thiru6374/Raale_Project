"""
app/pages/security_dashboard.py

System Security & Resilience Dashboard.
"""
import streamlit as st
from app.components.layout import apply_global_styles, page_header
from app.components.sidebar import render_sidebar
import pandas as pd
from datetime import datetime

from src.security.security_service import SecurityService
from src.security.roles import Role, ROLE_DISPLAY
from src.security.permissions import PERMISSION_MATRIX
from src.security.access_control import AccessControl
from src.security.permissions import PERM_CREATE_BACKUP, PERM_RESTORE_BACKUP
from src.services.backup_service import BackupService
from src.services.startup_validator import run_startup_validation
from src.services.persistence.jsonl_store import JSONLStore



# ── Premium styling ───────────────────────────────────────────────────────────
st.markdown("""
<style>
  .sec-card { background:#1a2035; border-radius:10px; padding:15px; margin-bottom:12px;
        border:1px solid #2d3748; }
  .sec-healthy { border-left:4px solid #00CC96; }
  .sec-warning { border-left:4px solid #FFC107; }
  .sec-critical { border-left:4px solid #FF4B4B; }
  .sec-missing { border-left:4px solid #888; }
  .badge-green { color:#00CC96; font-weight:700; }
  .badge-yellow{ color:#FFC107; font-weight:700; }
  .badge-red  { color:#FF4B4B; font-weight:700; }
</style>
""", unsafe_allow_html=True)

page_header(" System Security & Resilience", subtitle=None, icon=":material/security:")

# Role selector
role = SecurityService.render_role_selector(sidebar=True)
st.sidebar.markdown("---")
st.sidebar.info(
  "**PROTOTYPE NOTICE**: Role simulation only. \n"
  "Not a production authentication system. \n"
  "No passwords or identity verification exist."
)

# ── SECTION 1: Current Role & Access Level ───────────────────────────────────
st.subheader(" Current Session")
c_role1, c_role2 = st.columns([1, 2])
with c_role1:
  st.metric("Active Role", role.value)
  st.caption(ROLE_DISPLAY[role])
with c_role2:
  perms = sorted(PERMISSION_MATRIX[role])
  st.markdown("**Granted Permissions:**")
  for p in perms:
    st.markdown(f"  `{p}`")

st.markdown("---")

# ── SECTION 2: Startup & Environment Health ───────────────────────────────────
st.subheader(" Environment & Startup Validation")
with st.spinner("Running startup validation…"):
  startup = run_startup_validation()

overall_color = {"HEALTHY": "badge-green", "WARNING": "badge-yellow", "CRITICAL": "badge-red"}.get(startup["overall"], "badge-yellow")
st.markdown(f"**Overall Status:** <span class='{overall_color}'>{startup['overall']}</span>", unsafe_allow_html=True)

checks_df = pd.DataFrame(startup["checks"])
# Colour rows
def _row_style(row):
  c = {"HEALTHY": "color: #00CC96", "WARNING": "color: #FFC107", "CRITICAL": "color: #FF4B4B"}.get(row["status"], "")
  return [c] * len(row)

st.dataframe(
  checks_df.style.apply(_row_style, axis=1),
  use_container_width=True,
  hide_index=True,
)

st.markdown("---")

# ── SECTION 3: Persistence Health ────────────────────────────────────────────
st.subheader(" Persistence Health (JSONL Stores)")

stores_to_check = {
  "Alerts":     "data/intelligence/alerts.jsonl",
  "Feedback":    "data/intelligence/feedback.jsonl",
  "Proposals":    "data/intelligence/improvement_proposals.jsonl",
  "Security Audit": "data/intelligence/security_audit.jsonl",
  "Config Versions": "data/config/settings_versioned.jsonl",
  "Config Audit":  "data/config/config_audit.jsonl",
}

health_rows = []
for name, path in stores_to_check.items():
  store = JSONLStore(path)
  health = store.health_status()
  health_rows.append({
    "Store":     name,
    "Status":     health["status"],
    "Records":    health["record_count"],
    "Exists":     "" if health["exists"] else "",
    "Writable":    "" if health["writable"] else "",
    "SHA-256 (prefix)": store.compute_checksum()[:16] or "—",
  })

health_df = pd.DataFrame(health_rows)
st.dataframe(health_df, use_container_width=True, hide_index=True)

st.markdown("---")

# ── SECTION 4: Security Audit Events ─────────────────────────────────────────
st.subheader(" Recent Security Events")
events = AccessControl.get_recent_events(30)
denials = AccessControl.get_denial_count()
st.metric("Total Access Denials (last 500 events)", denials)

if events:
  ev_df = pd.DataFrame(events)[["timestamp", "event_type", "actor_role", "action", "result", "reason"]]
  st.dataframe(ev_df.iloc[::-1].reset_index(drop=True), use_container_width=True, hide_index=True)
else:
  st.info("No security events recorded yet.")

st.markdown("---")

# ── SECTION 5: Backup Management ─────────────────────────────────────────────
st.subheader(" Backup & Recovery")

backups = BackupService.list_backups()
if backups:
  b_df = pd.DataFrame(backups)[["filename", "size_kb", "modified_at"]]
  b_df.columns = ["Backup File", "Size (KB)", "Created At"]
  st.dataframe(b_df, use_container_width=True, hide_index=True)
  latest_backup = backups[-1]["filename"]
  st.caption(f"Latest backup: **{latest_backup}**")
else:
  st.info("No backups found. Create one below.")
  latest_backup = None

col_b1, col_b2 = st.columns(2)
with col_b1:
  st.markdown("**Create Backup**")
  backup_label = st.text_input("Backup label (optional)", placeholder="e.g. before_config_change")
  if st.button(" Create Backup Now"):
    ok, msg = AccessControl.require(role, PERM_CREATE_BACKUP, action="create_backup")
    if not ok:
      SecurityService.access_denied_message(msg)
    else:
      with st.spinner("Creating backup…"):
        result = BackupService.create_backup(label=backup_label)
      if result.get("status") == "OK":
        AccessControl.log_action("BACKUP_CREATED", role, "create_backup",
                     resource=result.get("filename", ""))
        st.success(f" Backup created: `{result['filename']}` ({result['size_kb']} KB)")
        st.rerun()
      else:
        st.error(f"Backup failed. Check logs. Reason: {result.get('reason')}")

with col_b2:
  st.markdown("**Validate Backup**")
  if backups:
    selected_bname = st.selectbox("Select backup to validate", [b["filename"] for b in backups])
    selected_bpath = next(b["path"] for b in backups if b["filename"] == selected_bname)
    if st.button(" Validate Backup"):
      validation = BackupService.validate_backup(selected_bpath)
      if validation.get("valid"):
        st.success(f" Backup is valid. SHA-256: `{validation['sha256'][:20]}…`")
      else:
        st.error(f" Backup invalid: {validation.get('reason')}")

st.markdown("**Restore Backup** — requires ADMIN role")
if backups:
  restore_bname = st.selectbox("Select backup to restore", [b["filename"] for b in backups], key="restore_sel")
  restore_bpath = next(b["path"] for b in backups if b["filename"] == restore_bname)
  restore_reason = st.text_input("Reason for restore", placeholder="e.g. corrupted config after failed update")
  if st.button(" Restore Selected Backup", type="primary"):
    from src.security.input_validator import validate_text_input
    ok_perm, msg_perm = AccessControl.require(role, PERM_RESTORE_BACKUP, action="restore_backup")
    ok_in, msg_in = validate_text_input(restore_reason, "restore_reason", required=True)
    if not ok_perm:
      SecurityService.access_denied_message(msg_perm)
    elif not ok_in:
      st.warning(f"Input error: {msg_in}")
    else:
      with st.spinner("Restoring backup (pre-restore safety backup will be created)…"):
        result = BackupService.restore_backup(restore_bpath, actor_role=role.value)
      if result.get("status") == "OK":
        AccessControl.log_action("BACKUP_RESTORED", role, "restore_backup",
                     resource=restore_bname, reason=restore_reason)
        st.success(f" Restore complete. Safety backup: `{result.get('safety_backup')}`")
      else:
        st.error(f" Restore failed. {result.get('reason')}")

st.markdown("---")

# ── SECTION 6: Known Limitations ─────────────────────────────────────────────
with st.expander(" Known Prototype Security Limitations"):
  st.markdown("""
| Limitation | Description | Production Recommendation |
|---|---|---|
| **No Authentication** | Role is selected in UI; no identity verification | Integrate OAuth 2.0 / LDAP / managed auth |
| **No Password Storage** | No user accounts exist | Use a proper identity provider |
| **No Session Tokens** | Roles reset when browser is refreshed | Use server-side session management |
| **JSONL Concurrency** | Not safe for concurrent multi-user writes | Replace with PostgreSQL |
| **Local Backup Only** | Backups stored on same machine as data | Use off-site cloud storage (e.g. S3) |
| **No Encryption at Rest** | JSONL files are plaintext | Encrypt at-rest in production |
| **No TLS** | Streamlit runs over HTTP locally | Deploy behind HTTPS reverse proxy in production |
| **No Rate Limiting** | No protection against API abuse | Add rate limiting at the infrastructure level |
""")

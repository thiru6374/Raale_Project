import re

with open('app/pages/overview.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Fix the columns: Move sched_col to its own full-width row
content = re.sub(
    r'map_col, compare_col, sched_col = st\.columns\(\[.*?\]\)',
    'map_col, compare_col = st.columns([2, 1.5])',
    content
)

# 2. Fix Section A: Heat-Risk Map
content = re.sub(
    r'st\.markdown\(\s*\"<div class=\'dash-section\'><h4>\"[ \t]*\n[ \t]*\"<span class=\'material-symbols-rounded\'>map</span>\"[ \t]*\n[ \t]*\"Heat-Risk Map \(Active Dataset\)</h4>\",[ \t]*\n[ \t]*unsafe_allow_html=True[ \t]*\n[ \t]*\)(.*?)\s*st\.markdown\(\"</div>\", unsafe_allow_html=True\)',
    r'with st.container(border=True):\n    st.markdown("<h4><span class=\'material-symbols-rounded\'>map</span>Heat-Risk Map (Active Dataset)</h4>", unsafe_allow_html=True)\1',
    content, flags=re.DOTALL
)

# 3. Fix Section B: Baseline vs Proposed
content = re.sub(
    r'st\.markdown\(\"<div class=\'dash-section\'><h4><span class=\'material-symbols-rounded\'>stacked_bar_chart</span>Baseline vs Proposed</h4>\", unsafe_allow_html=True\)(.*?)\s*st\.markdown\(\"</div>\", unsafe_allow_html=True\)',
    r'with st.container(border=True):\n    st.markdown("<h4><span class=\'material-symbols-rounded\'>stacked_bar_chart</span>Baseline vs Proposed</h4>", unsafe_allow_html=True)\1',
    content, flags=re.DOTALL
)

# 4. Fix Section C: Outreach Schedule
content = re.sub(
    r'with sched_col:\n\s*st\.markdown\(\"<div class=\'dash-section\'><h4><span class=\'material-symbols-rounded\'>schedule</span>Outreach Schedule \(Upcoming\)</h4>\", unsafe_allow_html=True\)(.*?)\s*st\.markdown\(\"</div>\", unsafe_allow_html=True\)',
    r'st.markdown("<br>", unsafe_allow_html=True)\nsched_col = st.container(border=True)\nwith sched_col:\n  st.markdown("<h4><span class=\'material-symbols-rounded\'>schedule</span>Outreach Schedule (Upcoming)</h4>", unsafe_allow_html=True)\1',
    content, flags=re.DOTALL
)

# 5. Fix Priority Table
content = re.sub(
    r'with pri_col:\n\s*st\.markdown\(\"<div class=\'dash-section\'>\", unsafe_allow_html=True\)\n\s*st\.markdown\(\"<h4><span class=\'material-symbols-rounded\'>priority_high</span>Top Priority Neighbourhoods</h4>\", unsafe_allow_html=True\)(.*?)\s*st\.markdown\(\"</div>\", unsafe_allow_html=True\)',
    r'with pri_col:\n  with st.container(border=True):\n    st.markdown("<h4><span class=\'material-symbols-rounded\'>priority_high</span>Top Priority Neighbourhoods</h4>", unsafe_allow_html=True)\1',
    content, flags=re.DOTALL
)

# 6. Fix Fairness
content = re.sub(
    r'with right_col:\n\s*# ── Fairness & Bias Summary ──.*\n\s*st\.markdown\(\"<div class=\'dash-section\'>\", unsafe_allow_html=True\)\n\s*st\.markdown\(\"<h4><span class=\'material-symbols-rounded\'>balance</span>Fairness &amp; Bias Summary</h4>\", unsafe_allow_html=True\)(.*?)\s*st\.markdown\(\"</div>\", unsafe_allow_html=True\)',
    r'with right_col:\n  # ── Fairness & Bias Summary ──\n  with st.container(border=True):\n    st.markdown("<h4><span class=\'material-symbols-rounded\'>balance</span>Fairness &amp; Bias Summary</h4>", unsafe_allow_html=True)\1',
    content, flags=re.DOTALL
)

# 7. Fix Comms
content = re.sub(
    r'# ── Communication Preview ──.*\n\s*st\.markdown\(\"<div class=\'dash-section\'>\", unsafe_allow_html=True\)\n\s*st\.markdown\(\"<h4><span class=\'material-symbols-rounded\'>campaign</span>Communication Preview</h4>\", unsafe_allow_html=True\)(.*?)\s*st\.markdown\(\"</div>\", unsafe_allow_html=True\)',
    r'# ── Communication Preview ──\n  with st.container(border=True):\n    st.markdown("<h4><span class=\'material-symbols-rounded\'>campaign</span>Communication Preview</h4>", unsafe_allow_html=True)\1',
    content, flags=re.DOTALL
)

# 8. Fix Alerts
content = re.sub(
    r'# ── Active Overrides & Alerts ──.*\n\s*st\.markdown\(\"<div class=\'dash-section\'>\", unsafe_allow_html=True\)\n\s*st\.markdown\(\"<h4><span class=\'material-symbols-rounded\'>warning</span>Active Overrides &amp; Alerts</h4>\", unsafe_allow_html=True\)(.*?)\s*st\.markdown\(\"</div>\", unsafe_allow_html=True\)',
    r'# ── Active Overrides & Alerts ──\n  with st.container(border=True):\n    st.markdown("<h4><span class=\'material-symbols-rounded\'>warning</span>Active Overrides &amp; Alerts</h4>", unsafe_allow_html=True)\1',
    content, flags=re.DOTALL
)

with open('app/pages/overview.py', 'w', encoding='utf-8') as f:
    f.write(content)
print("Finished rewriting containers in overview.py")

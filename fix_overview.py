import re

with open('app/pages/overview.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Fix Section A: Heat-Risk Map
content = re.sub(
    r'st\.markdown\("<div class=\'dash-section\'><h4><span class=\'material-symbols-rounded\'>map</span>Heat-Risk Map</h4>", unsafe_allow_html=True\)(.*?)\s*st\.markdown\("</div>", unsafe_allow_html=True\)',
    r'with st.container(border=True):\n    st.markdown("<h4><span class=\'material-symbols-rounded\'>map</span>Heat-Risk Map</h4>", unsafe_allow_html=True)\1',
    content, flags=re.DOTALL
)

# Fix Section B: Baseline vs Proposed
content = re.sub(
    r'st\.markdown\("<div class=\'dash-section\'><h4><span class=\'material-symbols-rounded\'>stacked_bar_chart</span>Baseline vs Proposed</h4>", unsafe_allow_html=True\)(.*?)\s*st\.markdown\("</div>", unsafe_allow_html=True\)',
    r'with st.container(border=True):\n    st.markdown("<h4><span class=\'material-symbols-rounded\'>stacked_bar_chart</span>Baseline vs Proposed</h4>", unsafe_allow_html=True)\1',
    content, flags=re.DOTALL
)

# Fix Section C: Outreach Schedule
content = re.sub(
    r'st\.markdown\("<div class=\'dash-section\'><h4><span class=\'material-symbols-rounded\'>schedule</span>Outreach Schedule \(Upcoming\)</h4>", unsafe_allow_html=True\)(.*?)\s*st\.markdown\("</div>", unsafe_allow_html=True\)',
    r'with st.container(border=True):\n    st.markdown("<h4><span class=\'material-symbols-rounded\'>schedule</span>Outreach Schedule (Upcoming)</h4>", unsafe_allow_html=True)\1',
    content, flags=re.DOTALL
)

# Fix Priority Table
content = re.sub(
    r'st\.markdown\("<div class=\'dash-section\'>", unsafe_allow_html=True\)\s*st\.markdown\("<h4><span class=\'material-symbols-rounded\'>priority_high</span>Top Priority Neighbourhoods</h4>", unsafe_allow_html=True\)(.*?)\s*st\.markdown\("</div>", unsafe_allow_html=True\)',
    r'with st.container(border=True):\n  st.markdown("<h4><span class=\'material-symbols-rounded\'>priority_high</span>Top Priority Neighbourhoods</h4>", unsafe_allow_html=True)\1',
    content, flags=re.DOTALL
)

# Fix Fairness
content = re.sub(
    r'st\.markdown\("<div class=\'dash-section\'>", unsafe_allow_html=True\)\s*st\.markdown\("<h4><span class=\'material-symbols-rounded\'>balance</span>Fairness &amp; Bias Summary</h4>", unsafe_allow_html=True\)(.*?)\s*st\.markdown\("</div>", unsafe_allow_html=True\)',
    r'with st.container(border=True):\n  st.markdown("<h4><span class=\'material-symbols-rounded\'>balance</span>Fairness &amp; Bias Summary</h4>", unsafe_allow_html=True)\1',
    content, flags=re.DOTALL
)

# Fix Comms
content = re.sub(
    r'st\.markdown\("<div class=\'dash-section\'>", unsafe_allow_html=True\)\s*st\.markdown\("<h4><span class=\'material-symbols-rounded\'>campaign</span>Communication Preview</h4>", unsafe_allow_html=True\)(.*?)\s*st\.markdown\("</div>", unsafe_allow_html=True\)',
    r'with st.container(border=True):\n  st.markdown("<h4><span class=\'material-symbols-rounded\'>campaign</span>Communication Preview</h4>", unsafe_allow_html=True)\1',
    content, flags=re.DOTALL
)

# Fix Alerts
content = re.sub(
    r'st\.markdown\("<div class=\'dash-section\'>", unsafe_allow_html=True\)\s*st\.markdown\("<h4><span class=\'material-symbols-rounded\'>warning</span>Active Overrides &amp; Alerts</h4>", unsafe_allow_html=True\)(.*?)\s*st\.markdown\("</div>", unsafe_allow_html=True\)',
    r'with st.container(border=True):\n  st.markdown("<h4><span class=\'material-symbols-rounded\'>warning</span>Active Overrides &amp; Alerts</h4>", unsafe_allow_html=True)\1',
    content, flags=re.DOTALL
)

with open('app/pages/overview.py', 'w', encoding='utf-8') as f:
    f.write(content)
print("done")

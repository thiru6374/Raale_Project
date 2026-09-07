"""
app/components/layout.py

Shared layout and CSS utilities for a consistent, premium design.
"""
import streamlit as st

def apply_global_styles():
    """Injects global CSS to match the reference design."""
    st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
        @import url('https://fonts.googleapis.com/css2?family=Material+Symbols+Rounded:opsz,wght,FILL,GRAD@24,400,0,0');
        
        .material-symbols-rounded {
          font-variation-settings: 'FILL' 0, 'wght' 400, 'GRAD' 0, 'opsz' 24;
          vertical-align: middle;
        }

        html, body, [class*="css"] {
            font-family: 'Inter', sans-serif;
            background-color: #f8fafc;
            color: #1e293b;
        }
        
        /* Modernized Sidebar */
        [data-testid="stSidebar"] {
            background-color: #0f172a;
            color: #f1f5f9;
        }
        [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p {
            color: #94a3b8;
            font-size: 0.85rem;
            text-transform: uppercase;
            font-weight: 600;
            letter-spacing: 0.05em;
            margin-top: 1rem;
            margin-bottom: 0.2rem;
        }
        /* Sidebar Links */
        [data-testid="stSidebarNav"] a {
            color: #e2e8f0 !important;
            border-radius: 8px;
            margin: 2px 10px;
            transition: background-color 0.2s;
        }
        [data-testid="stSidebarNav"] a:hover {
            background-color: rgba(255,255,255,0.1);
        }
        
        /* Premium Metric Cards */
        [data-testid="stMetric"] {
            background: #ffffff;
            border: 1px solid #e2e8f0;
            border-radius: 12px;
            padding: 20px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.05);
            transition: transform 0.2s, box-shadow 0.2s;
        }
        [data-testid="stMetric"]:hover {
            box-shadow: 0 4px 6px rgba(0,0,0,0.08);
            transform: translateY(-2px);
        }
        [data-testid="stMetricLabel"] {
            color: #64748b;
            font-size: 0.9rem;
            font-weight: 500;
            text-transform: none;
        }
        [data-testid="stMetricValue"] {
            color: #0f172a;
            font-size: 2.2rem;
            font-weight: 700;
        }
        
        /* Cleaner dataframes */
        [data-testid="stDataFrame"] {
            border-radius: 12px;
            border: 1px solid #e2e8f0;
            overflow: hidden;
            box-shadow: 0 1px 3px rgba(0,0,0,0.05);
        }
        
        /* Buttons */
        .stButton button {
            border-radius: 8px;
            font-weight: 500;
            border: 1px solid #cbd5e1;
            background-color: #ffffff;
            color: #0f172a;
            transition: all 0.2s;
        }
        .stButton button:hover {
            border-color: #3b82f6;
            color: #3b82f6;
            background-color: #f0f9ff;
        }
        
        /* Primary button */
        .stButton button[kind="primary"] {
            background-color: #2563eb;
            color: white;
            border: none;
        }
        .stButton button[kind="primary"]:hover {
            background-color: #1d4ed8;
            color: white;
        }

        /* Status Badges */
        .badge {
            padding: 4px 10px;
            border-radius: 12px;
            font-size: 0.75rem;
            font-weight: 600;
            display: inline-block;
        }
        .badge.critical { background: #fee2e2; color: #ef4444; }
        .badge.warning { background: #fef3c7; color: #f59e0b; }
        .badge.success { background: #dcfce3; color: #10b981; }
        .badge.info { background: #e0f2fe; color: #0ea5e9; }
        
        /* Section Headers */
        h1 { color: #0f172a; font-weight: 700; font-size: 2rem; margin-bottom: 0.5rem;}
        h2 { color: #1e293b; font-weight: 600; font-size: 1.5rem; margin-top: 1.5rem; margin-bottom: 1rem;}
        h3 { color: #334155; font-weight: 600; font-size: 1.25rem;}
        p.subtitle { color: #64748b; font-size: 1.1rem; margin-bottom: 2rem; }
    </style>
    """, unsafe_allow_html=True)

def page_header(title: str, subtitle: str = None, icon: str = None):
    """Renders a standard page header."""
    if icon:
        st.header(title, anchor=False, icon=icon)
    else:
        st.header(title, anchor=False)
        
    if subtitle:
        st.markdown(f"<p class='subtitle'>{subtitle}</p>", unsafe_allow_html=True)
    st.markdown("<hr style='margin-top: 5px; margin-bottom: 25px; border: 0; border-top: 1px solid #e2e8f0;'>", unsafe_allow_html=True)

def status_badge(text: str, level: str = "info") -> str:
    """Returns HTML for a status badge. Levels: critical, warning, success, info"""
    return f"<span class='badge {level}'>{text}</span>"

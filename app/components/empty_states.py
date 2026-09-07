"""
app/components/empty_states.py

Reusable UI components for empty or error states.
"""
import streamlit as st

def show_empty_state(icon: str, title: str, description: str):
    """Renders a clean empty state card."""
    st.markdown(f"""
    <div style="
        background: #ffffff;
        border: 1px dashed #cbd5e1;
        border-radius: 12px;
        padding: 40px;
        text-align: center;
        margin-top: 20px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.02);
    ">
        <div style="font-size: 3rem; margin-bottom: 10px;">{icon}</div>
        <h3 style="color: #0f172a; margin: 0 0 10px 0; font-size: 1.25rem;">{title}</h3>
        <p style="color: #64748b; margin: 0; font-size: 0.95rem;">{description}</p>
    </div>
    """, unsafe_allow_html=True)

def show_pipeline_uninitialized():
    """Renders the standard empty state when pipeline hasn't run."""
    show_empty_state(
        icon="⏳",
        title="No Analysis Data Available",
        description="The system is waiting for the latest analysis to be run. Please go to the Dashboard to initialize or refresh."
    )

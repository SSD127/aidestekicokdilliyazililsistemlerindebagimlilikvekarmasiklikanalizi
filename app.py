"""
Software Complexity Analysis Platform - Main Application
FRONTEND ENTRY POINT

This is the main Streamlit application file.
Your backend teammates should provide real API endpoints that return
data matching the structure in /backend_mock/mock_data.py
"""

import streamlit as st
import sys
from pathlib import Path

# Add frontend directory to path
sys.path.append(str(Path(__file__).parent / "frontend"))
sys.path.append(str(Path(__file__).parent / "backend_mock"))

from frontend.ui_components import render_header, render_sidebar, render_welcome_screen, render_footer
from frontend.dashboard import render_overview_tab, render_performance_tab, render_disk_space_tab, render_details_tab
from backend_mock.mock_data import (
    generate_complexity_data,
    generate_performance_metrics,
    generate_disk_space_data,
    generate_code_analysis_data,
    generate_file_metrics
)

# Page configuration
st.set_page_config(
    page_title="Software Complexity Analysis Platform",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
    <style>
    .main-header {
        font-size: 2.5rem;
        font-weight: 700;
        color: #1f2937;
        margin-bottom: 0.5rem;
    }
    .sub-header {
        font-size: 1.1rem;
        color: #6b7280;
        margin-bottom: 2rem;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 2rem;
    }
    .stTabs [data-baseweb="tab"] {
        height: 3rem;
        padding-left: 1.5rem;
        padding-right: 1.5rem;
    }
    </style>
""", unsafe_allow_html=True)

# Initialize session state
if 'analysis_data' not in st.session_state:
    st.session_state.analysis_data = None
if 'github_url' not in st.session_state:
    st.session_state.github_url = ""

# Render header
render_header()

# Render sidebar and get analysis trigger
analyze_triggered = render_sidebar()

# Handle analysis
if analyze_triggered:
    with st.spinner("Analyzing repository..."):
        # TODO: Replace this with real API calls to your backend
        # Example:
        # response = requests.post('http://your-api.com/analyze', json={'url': st.session_state.github_url})
        # st.session_state.analysis_data = response.json()

        # For now, using mock data
        st.session_state.analysis_data = {
            'complexity': generate_complexity_data(),
            'performance': generate_performance_metrics(),
            'disk_space': generate_disk_space_data(),
            'code_analysis': generate_code_analysis_data(),
            'file_metrics': generate_file_metrics()
        }
        st.success("Analysis complete!")

# Main content
if st.session_state.analysis_data:
    data = st.session_state.analysis_data

    # Display repository name
    repo_name = st.session_state.github_url.split('/')[-1] if st.session_state.github_url else "Repository"
    st.markdown(f"### Analyzing: **{repo_name}**")
    st.markdown(f"**URL:** {st.session_state.github_url}")
    st.divider()

    # Create tabs
    tab1, tab2, tab3, tab4 = st.tabs(["📊 Overview", "⚡ Performance", "💾 Disk Space", "📋 Details"])

    with tab1:
        render_overview_tab(data)

    with tab2:
        render_performance_tab(data)

    with tab3:
        render_disk_space_tab(data)

    with tab4:
        render_details_tab(data)

else:
    render_welcome_screen()

# Footer
render_footer()

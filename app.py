"""
Software Complexity Analysis Platform - Main Application
FRONTEND ENTRY POINT

Streamlit uygulaması; PolyMetric backend'inin POST /api/analyze sarmalayıcı
endpoint'ine senkron istek atar ve dönen AnalysisResult JSON'unu dashboard
bileşenlerine besler.
"""

import os
import sys
from pathlib import Path

import requests
import streamlit as st

sys.path.append(str(Path(__file__).parent / "frontend"))

from frontend.dashboard import (
    render_details_tab,
    render_hotspots_tab,
    render_overview_tab,
    render_performance_tab,
)
from frontend.ui_components import (
    render_footer,
    render_header,
    render_sidebar,
    render_welcome_screen,
)

BACKEND_URL = os.getenv("POLYMETRIC_API", "http://localhost:8000")
ANALYZE_TIMEOUT_SECONDS = int(os.getenv("POLYMETRIC_ANALYZE_TIMEOUT", "300"))

st.set_page_config(
    page_title="Software Complexity Analysis Platform",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

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

if 'analysis_data' not in st.session_state:
    st.session_state.analysis_data = None
if 'github_url' not in st.session_state:
    st.session_state.github_url = ""
if 'last_error' not in st.session_state:
    st.session_state.last_error = None

render_header()

analyze_triggered = render_sidebar()


def call_analyze_api(github_url: str, branch: str = "main") -> dict | None:
    """Backend POST /api/analyze sarmalayıcısını çağırır; başarılıysa AnalysisResult dict döner."""
    try:
        resp = requests.post(
            f"{BACKEND_URL}/api/analyze",
            json={"github_url": github_url, "branch": branch},
            timeout=ANALYZE_TIMEOUT_SECONDS,
        )
    except requests.exceptions.Timeout:
        st.session_state.last_error = (
            f"Backend cevap vermedi (timeout {ANALYZE_TIMEOUT_SECONDS}s). "
            "Repo cok buyuk olabilir veya backend yavas."
        )
        return None
    except requests.exceptions.ConnectionError as exc:
        st.session_state.last_error = (
            f"Backend'e baglanilamadi ({BACKEND_URL}). "
            f"uvicorn ayakta mi? Detay: {exc}"
        )
        return None

    if resp.status_code == 200:
        st.session_state.last_error = None
        return resp.json()

    try:
        detail = resp.json().get("detail", resp.text)
    except ValueError:
        detail = resp.text
    st.session_state.last_error = f"Backend hata kodu {resp.status_code}: {detail}"
    return None


if analyze_triggered:
    with st.spinner("Repo analiz ediliyor — clone, parse, metrik..."):
        result = call_analyze_api(st.session_state.github_url, branch="main")
        if result is not None:
            st.session_state.analysis_data = result
            st.success("Analiz tamamlandi.")

if st.session_state.last_error:
    st.error(st.session_state.last_error)

if st.session_state.analysis_data:
    data = st.session_state.analysis_data

    repo_name = st.session_state.github_url.split('/')[-1] if st.session_state.github_url else "Repository"
    st.markdown(f"### Analiz: **{repo_name}**")
    st.markdown(f"**URL:** {st.session_state.github_url}")
    st.markdown(
        f"**Branch:** `{data.get('branch_name', 'main')}` · "
        f"**Commit:** `{data.get('commit_hash', '?')}` · "
        f"**Parser:** `{data.get('parser_version', '?')}`"
    )
    st.divider()

    tab1, tab2, tab3, tab4 = st.tabs([
        "📊 Genel Bakış",
        "⚡ Karmaşıklık Dağılımı",
        "🔥 Hotspots",
        "📋 Detaylar",
    ])

    with tab1:
        render_overview_tab(data)
    with tab2:
        render_performance_tab(data)
    with tab3:
        render_hotspots_tab(data)
    with tab4:
        render_details_tab(data)

else:
    render_welcome_screen()

render_footer()

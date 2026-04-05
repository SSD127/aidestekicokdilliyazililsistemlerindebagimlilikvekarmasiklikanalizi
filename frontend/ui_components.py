"""
Frontend UI Components
Reusable UI elements for the application
"""

import streamlit as st


def render_header():
    """Render the main application header"""
    st.markdown(
        '<div class="main-header">📊 Software Complexity Analysis Platform</div>',
        unsafe_allow_html=True
    )
    st.markdown(
        '<div class="sub-header">Analyze code complexity, performance metrics, and disk space usage from GitHub repositories</div>',
        unsafe_allow_html=True
    )


def render_sidebar():
    """
    Render the sidebar with GitHub URL input
    Returns: bool - True if analyze button was clicked
    """
    with st.sidebar:
        st.header("🔗 Repository Input")
        st.write("Enter a GitHub repository URL to analyze")

        github_url = st.text_input(
            "GitHub URL",
            placeholder="https://github.com/username/repository",
            value=st.session_state.github_url,
            label_visibility="collapsed"
        )

        analyze_button = st.button(
            "🚀 Analyze Repository",
            use_container_width=True,
            type="primary"
        )

        if github_url and github_url != st.session_state.github_url:
            st.session_state.github_url = github_url

        st.divider()

        st.markdown("### 📚 About")
        st.write("This platform analyzes software repositories to provide insights on:")
        st.write("• Code complexity patterns")
        st.write("• Performance metrics")
        st.write("• Disk space usage")
        st.write("• Code quality indicators")

        st.divider()

        st.markdown("### ℹ️ Demo Mode")
        st.info("This is a demo application that generates realistic mock data for visualization purposes.")

    return analyze_button and github_url


def render_welcome_screen():
    """Render the welcome/landing screen when no analysis is loaded"""
    st.info("👆 Enter a GitHub repository URL in the sidebar and click 'Analyze Repository' to get started")

    st.markdown("### 🚀 Features")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("""
        #### 📊 Comprehensive Analysis
        - Code complexity heatmaps
        - Performance metrics (time & space complexity)
        - Disk space usage breakdown
        - Detailed code statistics
        """)

        st.markdown("""
        #### 📈 Visual Insights
        - Interactive charts and graphs
        - Color-coded complexity ratings
        - File-level metrics
        - Language distribution
        """)

    with col2:
        st.markdown("""
        #### 🔍 Quality Metrics
        - Code quality scores
        - Test coverage analysis
        - Documentation coverage
        - Security vulnerability detection
        """)

        st.markdown("""
        #### 💡 Actionable Data
        - Identify optimization opportunities
        - Find problematic code sections
        - Track technical debt
        - Monitor code health
        """)

    st.divider()

    st.markdown("### 📝 Example Repositories to Try")
    st.code("https://github.com/facebook/react")
    st.code("https://github.com/microsoft/vscode")
    st.code("https://github.com/tensorflow/tensorflow")


def render_footer():
    """Render the application footer"""
    st.divider()
    st.markdown("""
        <div style='text-align: center; color: #6b7280; padding: 2rem;'>
            <p>Software Complexity Analysis Platform v1.0 | Built with Streamlit & Python</p>
            <p>Demo application with mock data for visualization purposes</p>
        </div>
    """, unsafe_allow_html=True)


def render_metric_cards(metrics_data):
    """
    Render a row of metric cards
    Args:
        metrics_data: List of dicts with 'label', 'value', 'delta' keys
    """
    cols = st.columns(len(metrics_data))

    for col, metric in zip(cols, metrics_data):
        with col:
            st.metric(
                label=metric['label'],
                value=metric['value'],
                delta=metric.get('delta')
            )


def get_complexity_rating(score):
    """
    Get a visual rating for complexity score
    Args:
        score: Complexity score (0-100)
    Returns:
        str: Emoji and text rating
    """
    if score < 30:
        return "🟢 Low"
    elif score < 60:
        return "🟡 Medium"
    else:
        return "🔴 High"

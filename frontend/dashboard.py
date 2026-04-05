"""
Frontend Dashboard Components
Handles data visualization and presentation for each tab
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from frontend.ui_components import render_metric_cards, get_complexity_rating


def render_overview_tab(data):
    """
    Render the Overview tab with key metrics and complexity heatmap
    Args:
        data: Dictionary containing all analysis data
    """
    # Key metrics
    metrics = [
        {
            'label': 'Total Files',
            'value': f"{data['code_analysis']['total_files']:,}",
            'delta': 'Active'
        },
        {
            'label': 'Lines of Code',
            'value': f"{data['code_analysis']['total_lines']:,}",
            'delta': None
        },
        {
            'label': 'Avg Complexity',
            'value': f"{sum(f['complexity'] for f in data['complexity']) / len(data['complexity']):.1f}",
            'delta': None
        },
        {
            'label': 'Code Quality',
            'value': f"{data['code_analysis']['code_quality_score']}/100",
            'delta': 'Good' if data['code_analysis']['code_quality_score'] >= 70 else 'Needs Work'
        }
    ]

    render_metric_cards(metrics)
    st.divider()

    # Complexity Heatmap
    st.subheader("🗺️ Complexity Heatmap")
    st.write("Visual representation of code complexity across files (darker = more complex)")

    complexity_df = pd.DataFrame(data['complexity'])

    fig = go.Figure(data=go.Heatmap(
        z=[complexity_df['complexity'].values],
        x=complexity_df['name'].values,
        y=['Complexity'],
        colorscale=[
            [0, '#22c55e'],      # Green (low complexity)
            [0.3, '#84cc16'],    # Light green
            [0.5, '#eab308'],    # Yellow
            [0.7, '#f97316'],    # Orange
            [1, '#ef4444']       # Red (high complexity)
        ],
        text=[[f"{name}<br>Score: {score}" for name, score in zip(complexity_df['name'], complexity_df['complexity'])]],
        hovertemplate='%{text}<extra></extra>',
        colorbar=dict(title="Complexity Score")
    ))

    fig.update_layout(
        height=200,
        margin=dict(l=20, r=20, t=20, b=100),
        xaxis={'side': 'bottom', 'tickangle': -45},
        yaxis={'visible': False}
    )

    st.plotly_chart(fig, use_container_width=True)
    st.divider()

    # File Metrics Table
    st.subheader("📄 File Metrics")

    file_metrics_df = pd.DataFrame(data['file_metrics'])
    file_metrics_df['Complexity Rating'] = file_metrics_df['complexity'].apply(get_complexity_rating)

    st.dataframe(
        file_metrics_df[['file', 'lines', 'complexity', 'Complexity Rating', 'maintainability']],
        use_container_width=True,
        hide_index=True,
        column_config={
            'file': st.column_config.TextColumn('File Path', width="medium"),
            'lines': st.column_config.NumberColumn('Lines', width="small"),
            'complexity': st.column_config.ProgressColumn('Complexity Score', min_value=0, max_value=100, width="medium"),
            'Complexity Rating': st.column_config.TextColumn('Rating', width="small"),
            'maintainability': st.column_config.ProgressColumn('Maintainability', min_value=0, max_value=100, width="medium")
        }
    )


def render_performance_tab(data):
    """
    Render the Performance tab with time and space complexity analysis
    Args:
        data: Dictionary containing all analysis data
    """
    st.subheader("⚡ Performance Analysis")
    st.write("Time and space complexity analysis of your codebase")

    perf_data = data['performance']

    col1, col2 = st.columns(2)

    with col1:
        # Time Complexity Chart
        st.markdown("#### ⏱️ Time Complexity Distribution")

        time_complexity_df = pd.DataFrame(perf_data['time_complexity'])

        fig_time = px.pie(
            time_complexity_df,
            values='count',
            names='complexity',
            color='complexity',
            color_discrete_map={
                'O(1)': '#22c55e',
                'O(log n)': '#84cc16',
                'O(n)': '#eab308',
                'O(n log n)': '#f97316',
                'O(n²)': '#ef4444',
                'O(2^n)': '#dc2626'
            }
        )

        fig_time.update_traces(textposition='inside', textinfo='percent+label')
        fig_time.update_layout(height=400, showlegend=True)

        st.plotly_chart(fig_time, use_container_width=True)

    with col2:
        # Space Complexity Chart
        st.markdown("#### 💾 Space Complexity Distribution")

        space_complexity_df = pd.DataFrame(perf_data['space_complexity'])

        fig_space = px.pie(
            space_complexity_df,
            values='count',
            names='complexity',
            color='complexity',
            color_discrete_map={
                'O(1)': '#22c55e',
                'O(log n)': '#84cc16',
                'O(n)': '#eab308',
                'O(n²)': '#ef4444'
            }
        )

        fig_space.update_traces(textposition='inside', textinfo='percent+label')
        fig_space.update_layout(height=400, showlegend=True)

        st.plotly_chart(fig_space, use_container_width=True)

    st.divider()

    # Performance metrics
    metrics = [
        {
            'label': 'Average Execution Time',
            'value': f"{perf_data['avg_execution_time']}ms",
            'delta': None
        },
        {
            'label': 'Memory Usage',
            'value': f"{perf_data['memory_usage']}MB",
            'delta': None
        },
        {
            'label': 'Optimizable Functions',
            'value': str(perf_data['optimizable_functions']),
            'delta': None
        }
    ]

    render_metric_cards(metrics)


def render_disk_space_tab(data):
    """
    Render the Disk Space tab with storage analysis
    Args:
        data: Dictionary containing all analysis data
    """
    st.subheader("💾 Disk Space Analysis")
    st.write("Breakdown of disk usage by file type and directory")

    disk_data = data['disk_space']

    col1, col2 = st.columns([2, 1])

    with col1:
        # File type breakdown chart
        st.markdown("#### 📊 Storage by File Type")

        file_types_df = pd.DataFrame(disk_data['file_types'])

        fig_disk = px.bar(
            file_types_df,
            x='type',
            y='size_mb',
            color='size_mb',
            color_continuous_scale='Blues',
            labels={'size_mb': 'Size (MB)', 'type': 'File Type'}
        )

        fig_disk.update_layout(
            height=400,
            showlegend=False,
            xaxis_title="File Type",
            yaxis_title="Size (MB)"
        )

        st.plotly_chart(fig_disk, use_container_width=True)

    with col2:
        st.markdown("#### 📦 Total Size")

        metrics = [
            {
                'label': 'Repository Size',
                'value': f"{disk_data['total_size_mb']:.2f} MB",
                'delta': None
            },
            {
                'label': 'Estimated Install Size',
                'value': f"{disk_data['total_size_mb'] * 1.5:.2f} MB",
                'delta': None
            },
            {
                'label': 'Number of Files',
                'value': f"{disk_data['file_count']:,}",
                'delta': None
            }
        ]

        for metric in metrics:
            st.metric(
                label=metric['label'],
                value=metric['value'],
                delta=metric.get('delta')
            )

    st.divider()

    # Largest files
    st.markdown("#### 📁 Largest Files")

    largest_files_df = pd.DataFrame(disk_data['largest_files'])

    st.dataframe(
        largest_files_df,
        use_container_width=True,
        hide_index=True,
        column_config={
            'file': st.column_config.TextColumn('File Path', width="large"),
            'size_mb': st.column_config.NumberColumn('Size (MB)', format="%.2f MB", width="small")
        }
    )


def render_details_tab(data):
    """
    Render the Details tab with comprehensive code analysis
    Args:
        data: Dictionary containing all analysis data
    """
    st.subheader("📋 Detailed Code Analysis")

    code_data = data['code_analysis']

    # Statistics grid
    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown("##### 📊 Code Statistics")
        st.write(f"**Total Files:** {code_data['total_files']:,}")
        st.write(f"**Total Lines:** {code_data['total_lines']:,}")
        st.write(f"**Total Functions:** {code_data['total_functions']:,}")
        st.write(f"**Total Classes:** {code_data['total_classes']:,}")

    with col2:
        st.markdown("##### 📈 Quality Metrics")
        st.write(f"**Code Quality Score:** {code_data['code_quality_score']}/100")
        st.write(f"**Test Coverage:** {code_data['test_coverage']}%")
        st.write(f"**Documentation:** {code_data['documentation_coverage']}%")
        st.write(f"**Duplication Rate:** {code_data['duplication_rate']}%")

    with col3:
        st.markdown("##### ⚠️ Issues")
        st.write(f"**Critical Issues:** {code_data['issues']['critical']}")
        st.write(f"**Warnings:** {code_data['issues']['warnings']}")
        st.write(f"**Code Smells:** {code_data['issues']['code_smells']}")
        st.write(f"**Security Hotspots:** {code_data['issues']['security_hotspots']}")

    st.divider()

    # Language breakdown
    st.markdown("#### 💻 Language Distribution")

    languages_df = pd.DataFrame(code_data['languages'])

    fig_lang = px.bar(
        languages_df,
        x='language',
        y='percentage',
        color='language',
        labels={'percentage': 'Percentage (%)', 'language': 'Language'}
    )

    fig_lang.update_layout(
        height=300,
        showlegend=False,
        xaxis_title="Programming Language",
        yaxis_title="Percentage (%)"
    )

    st.plotly_chart(fig_lang, use_container_width=True)

    st.divider()

    # Dependencies
    st.markdown("#### 📦 Dependencies Analysis")

    col1, col2 = st.columns(2)

    with col1:
        st.metric(
            label="Total Dependencies",
            value=code_data['dependencies']['total']
        )
        st.metric(
            label="Direct Dependencies",
            value=code_data['dependencies']['direct']
        )

    with col2:
        st.metric(
            label="Outdated Dependencies",
            value=code_data['dependencies']['outdated'],
            delta="Update recommended" if code_data['dependencies']['outdated'] > 0 else "All up to date"
        )
        st.metric(
            label="Vulnerable Dependencies",
            value=code_data['dependencies']['vulnerable'],
            delta="Security risk" if code_data['dependencies']['vulnerable'] > 0 else "Secure"
        )

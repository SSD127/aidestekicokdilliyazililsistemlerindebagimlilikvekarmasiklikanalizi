"""
Frontend Dashboard Components

Backend POST /api/analyze sarmalayıcısının döndürdüğü AnalysisResult JSON'u
dashboard tablarında görselleştirir.

Beklenen veri yapısı (özet):
    data = {
        "files": [{path, language, loc, complexity_score, dependency_count, ...}],
        "functions": [{file_path, function_name, cyclomatic_complexity,
                       halstead_score, loc, start_line, end_line, risk_score}],
        "dependencies": [...],
        "hotspots": [{file_path, function_name, risk_score, reason, rank}],
        "branch_name", "commit_hash", "parser_version", ...
    }
"""

from collections import Counter

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from frontend.ui_components import get_complexity_rating, render_metric_cards


def _cc_bucket(cc: int) -> str:
    if cc <= 5:
        return "low (<=5)"
    if cc <= 10:
        return "moderate (6-10)"
    if cc <= 20:
        return "high (11-20)"
    return "critical (>20)"


def _effort_bucket(effort: float) -> str:
    if effort < 1000:
        return "low (<1k)"
    if effort < 10_000:
        return "moderate (1k-10k)"
    if effort < 100_000:
        return "high (10k-100k)"
    return "critical (>=100k)"


def render_overview_tab(data: dict) -> None:
    """Genel istatistikler, dosya bazlı karmaşıklık ısı haritası ve dosya tablosu."""
    files = data.get("files", []) or []
    functions = data.get("functions", []) or []

    if not files:
        st.warning("Bu run icin dosya metrigi yok. Repo desteklenen bir dilde mi?")
        return

    avg_complexity = sum(f["complexity_score"] for f in files) / max(len(files), 1)
    total_loc = sum(f.get("loc", 0) for f in files)
    max_complexity = max((f["complexity_score"] for f in files), default=0)

    metrics = [
        {"label": "Toplam Dosya", "value": f"{len(files):,}", "delta": None},
        {"label": "Toplam Satır (LOC)", "value": f"{total_loc:,}", "delta": None},
        {"label": "Toplam Fonksiyon", "value": f"{len(functions):,}", "delta": None},
        {"label": "Ort. Dosya CC", "value": f"{avg_complexity:.1f}", "delta": f"max {max_complexity:.0f}"},
    ]
    render_metric_cards(metrics)
    st.divider()

    st.subheader("🗺️ Karmaşıklık Isı Haritası")
    st.write("Dosya başına McCabe Cyclomatic Complexity toplamı (koyu = daha karmaşık)")

    files_df = pd.DataFrame([
        {"path": f["path"], "complexity": f["complexity_score"], "loc": f.get("loc", 0)}
        for f in files
    ]).sort_values("complexity", ascending=False).head(40)

    if not files_df.empty:
        fig = go.Figure(data=go.Heatmap(
            z=[files_df["complexity"].values],
            x=files_df["path"].values,
            y=["Complexity"],
            colorscale=[
                [0, "#22c55e"],
                [0.3, "#84cc16"],
                [0.5, "#eab308"],
                [0.7, "#f97316"],
                [1, "#ef4444"],
            ],
            text=[[f"{p}<br>CC: {c}<br>LOC: {l}"
                   for p, c, l in zip(files_df["path"], files_df["complexity"], files_df["loc"])]],
            hovertemplate="%{text}<extra></extra>",
            colorbar=dict(title="CC"),
        ))
        fig.update_layout(height=220, margin=dict(l=20, r=20, t=20, b=120),
                          xaxis={"side": "bottom", "tickangle": -45},
                          yaxis={"visible": False})
        st.plotly_chart(fig, use_container_width=True)

    st.divider()

    st.subheader("📄 Dosya Metrikleri")
    table_df = pd.DataFrame([
        {
            "Dosya": f["path"],
            "Dil": f.get("language", "?"),
            "LOC": f.get("loc", 0),
            "Toplam CC": f["complexity_score"],
            "Bağımlılık": f.get("dependency_count", 0),
            "Maintainability": f.get("maintainability_index"),
        }
        for f in files
    ])
    table_df["Değerlendirme"] = table_df["Toplam CC"].apply(get_complexity_rating)

    st.dataframe(
        table_df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Dosya": st.column_config.TextColumn("Dosya", width="medium"),
            "Toplam CC": st.column_config.NumberColumn("Toplam CC", format="%d"),
            "LOC": st.column_config.NumberColumn("LOC", width="small"),
            "Bağımlılık": st.column_config.NumberColumn("Bağımlılık", width="small"),
            "Değerlendirme": st.column_config.TextColumn("Değerlendirme", width="small"),
        },
    )


def render_performance_tab(data: dict) -> None:
    """Fonksiyon bazlı CC ve Halstead Effort dağılımları."""
    functions = data.get("functions", []) or []

    st.subheader("⚡ Karmaşıklık Dağılımı")
    st.info(
        "O(1)/O(n) gibi asimptotik karmaşıklık otomatik tespit edilmez; bu sekmede "
        "fonksiyonların McCabe CC ve Halstead Effort dağılımı gösterilir."
    )

    if not functions:
        st.warning("Henuz fonksiyon metrigi yok.")
        return

    cc_counts = Counter(_cc_bucket(fn["cyclomatic_complexity"]) for fn in functions)
    effort_counts = Counter(_effort_bucket(fn.get("halstead_score", 0)) for fn in functions)

    bucket_order = [
        "low (<=5)", "moderate (6-10)", "high (11-20)", "critical (>20)",
    ]
    effort_order = [
        "low (<1k)", "moderate (1k-10k)", "high (10k-100k)", "critical (>=100k)",
    ]
    color_map = {
        "low (<=5)": "#22c55e", "low (<1k)": "#22c55e",
        "moderate (6-10)": "#eab308", "moderate (1k-10k)": "#eab308",
        "high (11-20)": "#f97316", "high (10k-100k)": "#f97316",
        "critical (>20)": "#ef4444", "critical (>=100k)": "#ef4444",
    }

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("#### ⏱️ McCabe CC Dağılımı")
        cc_df = pd.DataFrame([
            {"bucket": b, "count": cc_counts.get(b, 0)} for b in bucket_order
        ])
        fig_cc = px.pie(cc_df, values="count", names="bucket",
                        color="bucket", color_discrete_map=color_map)
        fig_cc.update_traces(textposition="inside", textinfo="percent+label")
        fig_cc.update_layout(height=400, showlegend=True)
        st.plotly_chart(fig_cc, use_container_width=True)

    with col2:
        st.markdown("#### 🧠 Halstead Effort Dağılımı")
        effort_df = pd.DataFrame([
            {"bucket": b, "count": effort_counts.get(b, 0)} for b in effort_order
        ])
        fig_eff = px.pie(effort_df, values="count", names="bucket",
                         color="bucket", color_discrete_map=color_map)
        fig_eff.update_traces(textposition="inside", textinfo="percent+label")
        fig_eff.update_layout(height=400, showlegend=True)
        st.plotly_chart(fig_eff, use_container_width=True)

    st.divider()

    avg_cc = sum(fn["cyclomatic_complexity"] for fn in functions) / len(functions)
    max_cc = max(fn["cyclomatic_complexity"] for fn in functions)
    total_effort = sum(fn.get("halstead_score", 0) for fn in functions)
    high_risk = sum(1 for fn in functions if fn["cyclomatic_complexity"] > 10)

    metrics = [
        {"label": "Ortalama CC", "value": f"{avg_cc:.2f}", "delta": None},
        {"label": "Maksimum CC", "value": f"{max_cc}", "delta": None},
        {"label": "Toplam Halstead Effort", "value": f"{total_effort:,.0f}", "delta": None},
        {"label": "CC > 10 Fonksiyon", "value": f"{high_risk}", "delta": None},
    ]
    render_metric_cards(metrics)


def render_hotspots_tab(data: dict) -> None:
    """En riskli fonksiyonların tablosu (backend payload_builder.build_hotspots'tan gelir)."""
    hotspots = data.get("hotspots", []) or []
    functions = data.get("functions", []) or []

    st.subheader("🔥 Risk Hotspots")
    st.write("Risk skoru en yüksek 5 fonksiyon. Refactor adayları.")

    if not hotspots:
        st.info("Bu run icin hotspot uretilmedi.")
    else:
        hot_df = pd.DataFrame(hotspots)
        hot_df = hot_df[["rank", "function_name", "file_path", "risk_score", "reason"]]
        hot_df.columns = ["#", "Fonksiyon", "Dosya", "Risk Skoru", "Sebep"]
        st.dataframe(
            hot_df, use_container_width=True, hide_index=True,
            column_config={
                "#": st.column_config.NumberColumn("#", width="small"),
                "Risk Skoru": st.column_config.NumberColumn("Risk Skoru", format="%.1f"),
            },
        )

    if functions:
        st.divider()
        st.markdown("#### 🧮 Tüm Fonksiyonlar (CC sıralı)")
        fn_df = pd.DataFrame([
            {
                "Fonksiyon": fn["function_name"],
                "Dosya": fn["file_path"],
                "CC": fn["cyclomatic_complexity"],
                "Halstead Effort": fn.get("halstead_score", 0),
                "LOC": fn.get("loc", 0),
                "Risk Skoru": fn.get("risk_score", 0),
                "Satır": f"{fn.get('start_line', 1)}-{fn.get('end_line', 1)}",
            }
            for fn in functions
        ]).sort_values("CC", ascending=False).head(50)

        st.dataframe(
            fn_df, use_container_width=True, hide_index=True,
            column_config={
                "CC": st.column_config.ProgressColumn(
                    "CC", min_value=0, max_value=max(fn_df["CC"].max(), 1),
                ),
                "Halstead Effort": st.column_config.NumberColumn(
                    "Halstead Effort", format="%.0f",
                ),
                "Risk Skoru": st.column_config.NumberColumn("Risk", format="%.1f"),
            },
        )


def render_details_tab(data: dict) -> None:
    """Genel istatistikler, dil dağılımı, bağımlılık özeti."""
    files = data.get("files", []) or []
    functions = data.get("functions", []) or []
    dependencies = data.get("dependencies", []) or []

    st.subheader("📋 Detaylı Kod Analizi")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown("##### 📊 Kod İstatistikleri")
        st.write(f"**Toplam Dosya:** {len(files):,}")
        st.write(f"**Toplam LOC:** {sum(f.get('loc', 0) for f in files):,}")
        st.write(f"**Toplam Fonksiyon:** {len(functions):,}")
        st.write(f"**Toplam Bağımlılık Kenarı:** {len(dependencies):,}")

    with col2:
        st.markdown("##### 📈 Karmaşıklık")
        if functions:
            avg_cc = sum(fn["cyclomatic_complexity"] for fn in functions) / len(functions)
            max_cc = max(fn["cyclomatic_complexity"] for fn in functions)
            avg_effort = sum(fn.get("halstead_score", 0) for fn in functions) / len(functions)
            st.write(f"**Ortalama CC:** {avg_cc:.2f}")
            st.write(f"**Max CC:** {max_cc}")
            st.write(f"**Ort. Halstead Effort:** {avg_effort:,.0f}")
        else:
            st.write("Fonksiyon yok.")

    with col3:
        st.markdown("##### ⚠️ Risk Dağılımı")
        if functions:
            risk_buckets = Counter(_cc_bucket(fn["cyclomatic_complexity"]) for fn in functions)
            for bucket in ["critical (>20)", "high (11-20)", "moderate (6-10)", "low (<=5)"]:
                st.write(f"**{bucket}:** {risk_buckets.get(bucket, 0)}")
        else:
            st.write("—")

    st.divider()

    st.markdown("#### 💻 Dil Dağılımı")
    if files:
        lang_loc: Counter[str] = Counter()
        for f in files:
            lang_loc[f.get("language", "unknown")] += f.get("loc", 0)
        total_loc = sum(lang_loc.values()) or 1
        languages_df = pd.DataFrame([
            {
                "Dil": lang,
                "LOC": loc,
                "Yüzde": round(loc * 100 / total_loc, 2),
            }
            for lang, loc in lang_loc.most_common()
        ])

        fig_lang = px.bar(
            languages_df, x="Dil", y="Yüzde", color="Dil",
            labels={"Yüzde": "Yüzde (%)"},
        )
        fig_lang.update_layout(height=300, showlegend=False)
        st.plotly_chart(fig_lang, use_container_width=True)

        st.dataframe(languages_df, use_container_width=True, hide_index=True)
    else:
        st.info("Dil verisi yok.")

    st.divider()

    st.markdown("#### 📦 Bağımlılık Özeti")
    if dependencies:
        out_degree: Counter[str] = Counter(d["source_path"] for d in dependencies)
        in_degree: Counter[str] = Counter(d["target_path"] for d in dependencies)

        cdep1, cdep2 = st.columns(2)
        with cdep1:
            st.markdown("**En Çok İmport Eden 10 Dosya**")
            top_out = pd.DataFrame(out_degree.most_common(10), columns=["Dosya", "Import Sayısı"])
            st.dataframe(top_out, use_container_width=True, hide_index=True)
        with cdep2:
            st.markdown("**En Çok İmport Edilen 10 Dosya**")
            top_in = pd.DataFrame(in_degree.most_common(10), columns=["Dosya", "Bağımlı Sayısı"])
            st.dataframe(top_in, use_container_width=True, hide_index=True)
    else:
        st.info("Repo içi bağımlılık tespit edilmedi.")

    st.divider()
    st.caption(
        "Not: test_coverage, documentation_coverage, security_hotspots, vulnerable_dependencies "
        "metrikleri henüz desteklenmiyor (pylint/coverage/bandit entegrasyonu sonraki sprintte)."
    )

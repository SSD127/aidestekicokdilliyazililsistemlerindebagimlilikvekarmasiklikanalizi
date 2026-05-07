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
import streamlit.components.v1 as components

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
                    "CC", min_value=0, max_value=int(max(fn_df["CC"].max(), 1)),
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

# ─── NETWORK ANALYSIS SEKMESİ ───
# Bu fonksiyon, Bağımlılık Haritalama görevinin frontend görselleştirme kısmıdır.
# 4 bölüm: Özet kartlar, Döngü listesi, Metrikler, İnteraktif grafik
def render_network_tab(data: dict) -> None:
    """Bağımlılık Haritalama ve Network Analysis sekmesini oluşturur.

    Backend'den gelen analiz verilerini kullanarak projenin mimari
    bağımlılık haritasını görselleştirir.

    Args:
        data: Backend'in döndürdüğü AnalysisResult JSON verisi.
    """
    # Backend'den gelen verileri al
    dependencies = data.get("dependencies", [])     # Dosyalar arası import ilişkileri
    cycles = data.get("cycles", [])                 # Döngüsel bağımlılıklar
    metrics = data.get("graph_metrics", {})          # Grafik metrikleri

    st.subheader("🕸️ Mimari Bağımlılık Haritası")
    st.write("Dosyalar arasındaki import ilişkileri ve döngüsel bağımlılık analizi.")

    if not dependencies:
        st.info("Bağımlılık verisi bulunamadı.")
        return

    # ─── BÖLÜM 1: Özet Metrik Kartları ───
    # 4 sütunlu kart düzeni ile temel grafik istatistiklerini gösterir
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Toplam Düğüm", metrics.get("total_nodes", 0))
    with col2:
        st.metric("Toplam Bağlantı", metrics.get("total_edges", 0))
    with col3:
        st.metric("Döngü Sayısı", len(cycles), delta=f"{len(cycles)} ⚠️" if cycles else "0 ✅", delta_color="inverse")
    with col4:
        st.metric("Grafik Yoğunluğu", f"{metrics.get('density', 0):.4f}")

    st.divider()

    # ─── BÖLÜM 2: Döngüsel Bağımlılık Analizi ───
    # Tespit edilen döngüleri açılabilir paneller içinde listeler
    st.markdown("#### 🔍 Döngüsel Bağımlılık Tespiti")
    if cycles:
        st.warning(f"Sistemde {len(cycles)} adet döngüsel bağımlılık tespit edildi! Bu durum spagetti kod riskini artırır.")
        for i, cycle in enumerate(cycles, 1):
            with st.expander(f"Döngü #{i}: {cycle.get('chain')}"):
                st.write("**Dahil olan dosyalar:**")
                for node in cycle.get("nodes", []):
                    st.write(f"- `{node}`")
    else:
        st.success("✅ Tebrikler! Sistemde herhangi bir döngüsel bağımlılık bulunamadı.")

    st.divider()

    # ─── BÖLÜM 3: Mimari Metrikler ve Kararsızlık ───
    # Sol: genel metrikler, Sağ: instability tablosu
    col_m1, col_m2 = st.columns(2)
    with col_m1:
        st.markdown("#### 📈 Mimari Metrikler")
        st.write(f"**Güçlü Bağlı Bileşenler (SCC):** {metrics.get('strongly_connected_components', 0)}")
        st.write(f"**Ortalama Gelen Bağlantı:** {metrics.get('avg_in_degree', 0)}")
        st.write(f"**Ortalama Giden Bağlantı:** {metrics.get('avg_out_degree', 0)}")
        
        max_in = metrics.get("max_in_degree", {})
        st.write(f"**En Çok Bağımlılık Alan:** `{max_in.get('node', '-')}` ({max_in.get('degree', 0)})")
        
        max_out = metrics.get("max_out_degree", {})
        st.write(f"**En Çok Bağımlı Olan:** `{max_out.get('node', '-')}` ({max_out.get('degree', 0)})")

    with col_m2:
        st.markdown("#### ⚖️ Kararsızlık Skorları (Instability)")
        st.info("I = Ce / (Ca + Ce). 0 = Stabil, 1 = Kararsız. Stabil modüllerin değiştirilmesi zordur.")
        instability = metrics.get("instability_scores", {})
        if instability:
            inst_df = pd.DataFrame([
                {"Dosya": k, "Skor": v} for k, v in instability.items()
            ]).sort_values("Skor", ascending=False).head(10)
            st.dataframe(inst_df, use_container_width=True, hide_index=True)

    st.divider()

    # ─── BÖLÜM 4: İnteraktif Bağımlılık Grafiği (Pyvis) ───
    # Renk: Yeşil=proje dosyası, Gri=dış kütüphane, Kırmızı=döngüsel
    st.markdown("#### 🗺️ İnteraktif Bağımlılık Ağı")
    try:
        from pyvis.network import Network
        import tempfile

        # Grafik oluştur
        net = Network(height="600px", width="100%", directed=True, bgcolor="#ffffff", font_color="#333333")
        
        # Düğümleri ekle
        nodes = data.get("nodes", []) # Bu verinin AnalysisResult'da olması lazım, şemayı güncellemiştim
        if not nodes:
            # Fallback: dependencielerden çıkar
            node_ids = set()
            for d in dependencies:
                node_ids.add(d["source_path"])
                node_ids.add(d["target_path"])
            for nid in node_ids:
                net.add_node(nid, label=nid, size=20)
        else:
            for n in nodes:
                is_in_cycle = any(n["id"] in c["nodes"] for c in cycles)
                color = "#ef4444" if is_in_cycle else ("#22c55e" if n.get("type") == "project" else "#94a3b8")
                net.add_node(n["id"], label=n["id"], color=color, size=25 if n.get("type") == "project" else 15)

        # Kenarları ekle
        for d in dependencies:
            is_cycle_edge = False
            for c in cycles:
                c_nodes = c["nodes"]
                for i in range(len(c_nodes)):
                    if d["source_path"] == c_nodes[i] and d["target_path"] == c_nodes[(i+1)%len(c_nodes)]:
                        is_cycle_edge = True
                        break
            
            net.add_edge(
                d["source_path"], 
                d["target_path"], 
                color="#ef4444" if is_cycle_edge else "#cbd5e1",
                width=3 if is_cycle_edge else 1
            )

        # Geçici dosyaya kaydet ve oku
        with tempfile.NamedTemporaryFile(delete=False, suffix=".html") as tmp:
            net.save_graph(tmp.name)
            with open(tmp.name, 'r', encoding='utf-8') as f:
                html_content = f.read()
            components.html(html_content, height=650)
            
    except ImportError:
        st.warning("Pyvis kütüphanesi yüklü değil. Grafik görselleştirilemiyor.")
        st.write("Bağımlılık listesi:")
        st.dataframe(pd.DataFrame(dependencies))

import os
import sys
import tkinter as tk
from tkinter import filedialog

import networkx as nx
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

from analyzer import get_python_files, extract_imports
from graph import build_dependency_graph, find_circular_dependencies


def print_dependency_list(project_path: str) -> nx.DiGraph:
    files = get_python_files(project_path)

    print("\n" + "═" * 50)
    print(" BAĞIMLILIK LİSTESİ (Dosya → Import)")
    print("═" * 50)

    G = nx.DiGraph()

    for file in files:
        clean = os.path.basename(file).replace(".py", "")
        G.add_node(clean)
        imports = extract_imports(file)

        print(f"\n  📄 {os.path.basename(file)}")
        if imports:
            for imp in imports:
                G.add_edge(clean, imp)
                print(f"      └──▶ {imp}")
        else:
            print("      └── (bağımlılık yok)")

    print("\n" + "═" * 50)
    print(f"  Toplam Düğüm (node)  : {G.number_of_nodes()}")
    print(f"  Toplam Bağlantı (edge): {G.number_of_edges()}")
    print("═" * 50 + "\n")

    return G


# ─────────────────────────────────────────────
# 2) Döngüsel bağımlılık raporu
# ─────────────────────────────────────────────
def print_cycle_report(G: nx.DiGraph) -> list:
    """Varsa döngüsel bağımlılıkları bulur ve terminale yazar."""
    cycles = find_circular_dependencies(G)

    print("    DÖNGÜSEL BAĞIMLILIK ANALİZİ")
    print("─" * 50)

    if cycles:
        print(f"  ⚠️  {len(cycles)} döngü tespit edildi!\n")
        for i, cycle in enumerate(cycles, 1):
            path = " ──▶ ".join(cycle) + f" ──▶ {cycle[0]}"
            print(f"  [{i}] {path}")
    else:
        print(" Döngüsel bağımlılık bulunamadı.")

    print("─" * 50 + "\n")
    return cycles


# ─────────────────────────────────────────────
# 3) Graf çizimi (ana görsel çıktı)
# ─────────────────────────────────────────────
def draw_graph(G: nx.DiGraph, cycles: list, title: str = "Bağımlılık Haritası"):
    """
    NetworkX grafiğini renkli, okunabilir Matplotlib penceresinde çizer.

    Renk kodlaması:
      Kırmızı düğüm  → Döngüsel bağımlılığa dahil
      Yeşil düğüm   → Proje dosyası (temiz)
      Gri düğüm     → Dış kütüphane (os, sys, numpy gibi)
      Kırmızı ok    → Döngüsel bağlantı
      Siyah ok      → Normal bağımlılık
    """
    if G.number_of_nodes() == 0:
        print("  ⚠️  Grafik boş, çizilecek bir şey yok.")
        return

    #Döngüdeki düğümleri ve kenarları belirle
    cycle_nodes = set()
    cycle_edges = set()
    for cycle in cycles:
        cycle_nodes.update(cycle)
        for i in range(len(cycle)):
            cycle_edges.add((cycle[i], cycle[(i + 1) % len(cycle)]))

    # Proje içi dosyaları bul
    project_nodes = {
        n.replace(".py", "") for n in
        [os.path.basename(f) for f in get_python_files(_current_project_path)]
    }

    #Düğüm renkleri
    node_colors = []
    for node in G.nodes():
        if node in cycle_nodes:
            node_colors.append("#FF4C4C")   # Kırmızı: döngüsel
        elif node in project_nodes:
            node_colors.append("#4CAF50")   # Yeşil: proje dosyası
        else:
            node_colors.append("#B0BEC5")   # Gri: dış lib

    edge_colors = [
        "#FF4C4C" if (u, v) in cycle_edges else "#455A64"
        for u, v in G.edges()
    ]
    edge_widths = [
        2.5 if (u, v) in cycle_edges else 1.2
        for u, v in G.edges()
    ]

    if G.number_of_nodes() <= 6:
        pos = nx.spring_layout(G, seed=42, k=2.5)
    else:
        try:
            pos = nx.kamada_kawai_layout(G)
        except Exception:
            pos = nx.spring_layout(G, seed=42)

    #Çizim     
    fig, ax = plt.subplots(figsize=(12, 8))
    fig.patch.set_facecolor("#1E1E2E")
    ax.set_facecolor("#1E1E2E")
    ax.set_title(title, color="white", fontsize=16, fontweight="bold", pad=20)

    nx.draw_networkx_nodes(
        G, pos, ax=ax,
        node_color=node_colors,
        node_size=2000,
        alpha=0.92
    )
    nx.draw_networkx_labels(
        G, pos, ax=ax,
        font_color="white",
        font_size=10,
        font_weight="bold"
    )
    nx.draw_networkx_edges(
        G, pos, ax=ax,
        edge_color=edge_colors,
        width=edge_widths,
        arrows=True,
        arrowsize=20,
        connectionstyle="arc3,rad=0.1",  
        min_source_margin=25,
        min_target_margin=25
    )

    legend_items = [
        mpatches.Patch(color="#4CAF50", label="Proje Dosyası"),
        mpatches.Patch(color="#B0BEC5", label="Dış Kütüphane"),
        mpatches.Patch(color="#FF4C4C", label="Döngüsel Bağımlılık ⚠️"),
    ]
    ax.legend(
        handles=legend_items,
        loc="upper left",
        facecolor="#2D2D3F",
        edgecolor="#555",
        labelcolor="white",
        fontsize=9
    )

    ax.axis("off")
    plt.tight_layout()
    plt.show()


# Proje yolu global referansı (draw_graph için)
_current_project_path = ""


# Ana giriş noktası
if __name__ == "__main__":
    # Klasör seçme
    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)

    print("\n📂  Lütfen analiz etmek istediğiniz projeyi seçin...")
    project_path = filedialog.askdirectory(title="Proje Klasörünü Seçin")

    if not project_path:
        print("  İşlem iptal edildi.")
        sys.exit()

    _current_project_path = project_path
    print(f"\n  Seçilen klasör: {project_path}\n")

    #Bağımlılık listesini terminale yaz + grafiği kur
    G = print_dependency_list(project_path)

    #Döngüsel bağımlılık raporu
    cycles = print_cycle_report(G)

    #Görsel grafik penceresini aç
    folder_name = os.path.basename(project_path) or "Proje"
    draw_graph(G, cycles, title=f"{folder_name} — Bağımlılık Haritası")

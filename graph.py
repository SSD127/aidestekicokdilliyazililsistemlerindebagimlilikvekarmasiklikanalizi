import networkx as nx
from analyzer import get_python_files, extract_imports
import os

def build_dependency_graph(project_path):
    G = nx.DiGraph() 
    
    files = get_python_files(project_path)
    
    # Sistemdeki tüm dosyalar tek tek taranır
    for file in files:
        clean_name = os.path.basename(file).replace('.py', '')
        
        # Bu dosya Grafiğe bir Node olarak eklenir
        if not G.has_node(clean_name):
            G.add_node(clean_name)
            
        imports = extract_imports(file)
        
        for imp in imports:
            # clean_name (A dosyası), imp'i (B dosyasını) çağırıyor.
            # O halde G.add_edge ile A'dan B'ye bir "Ok" (Çizgi) çekilir.
            G.add_edge(clean_name, imp)
            
    return G

def find_circular_dependencies(G):
    """Tarjan/DFS algoritması ile grafik üzerindeki kapalı döngüleri (hataları) bulur."""
    try:
        cycles = list(nx.simple_cycles(G))
        return cycles
    except nx.NetworkXNoCycle:
        return []

if __name__ == "__main__":
    import tkinter as tk
    from tkinter import filedialog
    import sys

    root = tk.Tk()
    root.withdraw()
    root.attributes('-topmost', True)
    
    print("Lütfen analiz etmek istediğiniz projenin klasörünü ekranda açılan pencereden seçin...")
    project_path = filedialog.askdirectory(title="Bağımlılık Analizi İçin Proje Klasörünü Seçin")
    
    if not project_path:
        print("İşlem iptal edildi. Hiçbir klasör seçilmedi.")
        sys.exit()
        
    print(f"\n📂 Seçilen Proje Yolu: {project_path}\n")
    
    print("1. Bağımlılıklar Yönlü Grafik (Directed Graph) Modeline Çevriliyor...")
    dependency_graph = build_dependency_graph(project_path)
    
    print(f"Toplam Dosya (Node) Sayısı: {dependency_graph.number_of_nodes()}")
    print(f"Toplam Bağımlılık Oku (Edge) Sayısı: {dependency_graph.number_of_edges()}\n")
    
    print("2. Spagetti Kod / Mimari Hatalar Analiz Ediliyor...")
    cycles = find_circular_dependencies(dependency_graph)
    
    # Eğer döngü/hata listesi boş değilse:
    if cycles:
        print("\n[!] UYARI: DÖNGÜSEL BAĞIMLILIK TESPİT EDİLDİ [!]")
        for cycle in cycles:
            # Döngü Halka şeklinde birleştirilir
            cycle_path = " -> ".join(cycle) + f" -> {cycle[0]}"
            print(f"Hata Zinciri İzolesi: {cycle_path}")
    else:
        print("\n✅ Süper! Herhangi bir döngüsel hata (circular dependency) bulunamadı.")

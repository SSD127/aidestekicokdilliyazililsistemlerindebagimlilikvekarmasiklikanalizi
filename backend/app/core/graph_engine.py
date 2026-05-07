"""
graph_engine.py — Bağımlılık Haritalama ve Grafik Analiz Motoru

Bu modül, dosyalar arasındaki içe aktarma (import) ilişkilerini analiz ederek
yönlü bir grafik (Directed Graph) yapısına dönüştürür. Döngüsel bağımlılıkları
tespit eder ve mimari metrikleri hesaplar.

GÖREV: Bağımlılık Haritalama ve Grafik Sorumlusu (Network Analysis)

Kullanılan Kütüphane:
    - NetworkX: Grafik veri yapısı ve algoritmaları için kullanılan Python kütüphanesi.
      Yönlü grafik (DiGraph), döngü tespiti (simple_cycles), yoğunluk (density),
      güçlü bağlı bileşenler (SCC) gibi fonksiyonlar bu kütüphaneden gelir.
"""

# ─────────────────────────────────────────────
# Gerekli kütüphanelerin içe aktarılması
# ─────────────────────────────────────────────
import networkx as nx                               # Grafik veri yapısı ve algoritmaları (yönlü grafik, döngü tespiti vb.)
from typing import List, Dict, Set, Tuple, Optional  # Python tip belirtme araçları (kodun okunabilirliği için)
from dataclasses import dataclass, field             # Veri sınıfı tanımlama aracı (otomatik __init__, __repr__ üretir)


# ─────────────────────────────────────────────────────────────────
# VERİ MODELİ 1: CycleInfo
# Bir döngüsel bağımlılık zincirini temsil eden veri sınıfı.
# Örnek: A → B → C → A şeklinde bir döngü varsa,
#         nodes = ["A", "B", "C"], length = 3, chain = "A → B → C → A"
# ─────────────────────────────────────────────────────────────────
@dataclass
class CycleInfo:
    """Bir döngüsel bağımlılık zincirinin temsili.

    Döngüsel bağımlılık (circular dependency), iki veya daha fazla dosyanın
    birbirini karşılıklı olarak import etmesidir. Bu durum yazılım mimarisinde
    "spagetti kod" olarak adlandırılır ve bakım zorluğuna yol açar.

    Attributes:
        nodes: Döngüye dahil olan dosya/modül adlarının listesi.
        length: Döngüdeki eleman sayısı (otomatik hesaplanır).
    """
    nodes: List[str]     # Döngüdeki düğüm (dosya) isimlerinin listesi
    length: int = 0      # Döngünün uzunluğu (kaç dosya dahil)

    def __post_init__(self):
        """Nesne oluşturulduktan sonra çağrılır, uzunluğu otomatik hesaplar."""
        self.length = len(self.nodes)

    @property
    def chain(self) -> str:
        """Döngüyü insan tarafından okunabilir zincir formatında döndürür.

        Örnek çıktı: "app.py → utils.py → config.py → app.py"
        Bu format, döngünün başladığı dosyaya geri döndüğünü gösterir.
        """
        return " → ".join(self.nodes) + f" → {self.nodes[0]}"

    def to_dict(self) -> dict:
        """Döngü bilgisini JSON'a çevrilebilir sözlük formatına dönüştürür.

        Bu metot, API üzerinden frontend'e veri gönderilirken kullanılır.
        """
        return {
            "nodes": self.nodes,       # Döngüdeki dosyalar
            "length": self.length,     # Döngü uzunluğu
            "chain": self.chain,       # İnsan okunur zincir formatı
        }


# ─────────────────────────────────────────────────────────────────
# VERİ MODELİ 2: GraphMetrics
# Bağımlılık grafiğinin mimari metriklerini tutan veri sınıfı.
# Bu metrikler projenin mimari sağlığını ölçmek için kullanılır.
# ─────────────────────────────────────────────────────────────────
@dataclass
class GraphMetrics:
    """Bağımlılık grafiğinin mimari metrikleri.

    Bu metrikler projenin ne kadar karmaşık ve bakımı zor olduğunu gösterir.
    Dashboard'da "Network Analysis" sekmesinde görüntülenir.

    Attributes:
        total_nodes: Grafikteki toplam düğüm sayısı (dosya + dış kütüphane).
        total_edges: Grafikteki toplam kenar sayısı (import bağlantıları).
        total_cycles: Tespit edilen döngüsel bağımlılık sayısı.
        density: Grafik yoğunluğu (0-1 arası). 1'e yakınsa çok fazla bağlantı var demek.
        avg_in_degree: Ortalama gelen bağlantı sayısı (bir dosyanın ortalama kaç dosya tarafından import edildiği).
        avg_out_degree: Ortalama giden bağlantı sayısı (bir dosyanın ortalama kaç dosyayı import ettiği).
        max_in_degree: En çok import edilen dosya ve import sayısı.
        max_out_degree: En çok import yapan dosya ve import sayısı.
        strongly_connected_components: Güçlü bağlı bileşen sayısı (karşılıklı erişilebilir düğüm grupları).
        instability_scores: Her dosya için kararsızlık skoru (Robert C. Martin formülü).
    """
    total_nodes: int = 0                                    # Toplam düğüm (dosya) sayısı
    total_edges: int = 0                                    # Toplam kenar (import bağlantısı) sayısı
    total_cycles: int = 0                                   # Döngüsel bağımlılık sayısı
    density: float = 0.0                                    # Grafik yoğunluğu (0=seyrek, 1=tam bağlı)
    avg_in_degree: float = 0.0                              # Ortalama gelen bağlantı (in-degree)
    avg_out_degree: float = 0.0                             # Ortalama giden bağlantı (out-degree)
    max_in_degree: Tuple[str, int] = ("", 0)                # En çok bağımlılığa sahip düğüm (dosya adı, sayı)
    max_out_degree: Tuple[str, int] = ("", 0)               # En çok başkasına bağımlı düğüm (dosya adı, sayı)
    strongly_connected_components: int = 0                  # Güçlü bağlı bileşen sayısı (SCC)
    instability_scores: Dict[str, float] = field(default_factory=dict)  # Dosya bazlı kararsızlık skorları

    def to_dict(self) -> dict:
        """Metrikleri JSON'a çevrilebilir sözlük formatına dönüştürür.

        Bu metot, API üzerinden frontend'e veri gönderilirken kullanılır.
        round() ile ondalık sayılar yuvarlanarak okunabilirlik artırılır.
        """
        return {
            "total_nodes": self.total_nodes,
            "total_edges": self.total_edges,
            "total_cycles": self.total_cycles,
            "density": round(self.density, 4),                  # 4 ondalık basamağa yuvarla
            "avg_in_degree": round(self.avg_in_degree, 2),      # 2 ondalık basamağa yuvarla
            "avg_out_degree": round(self.avg_out_degree, 2),
            "max_in_degree": {"node": self.max_in_degree[0], "degree": self.max_in_degree[1]},
            "max_out_degree": {"node": self.max_out_degree[0], "degree": self.max_out_degree[1]},
            "strongly_connected_components": self.strongly_connected_components,
            "instability_scores": {k: round(v, 3) for k, v in self.instability_scores.items()},
        }


# ─────────────────────────────────────────────────────────────────
# ANA SINIF: GraphAnalyzer
# Bağımlılık ilişkilerini modelleyen, analiz eden ve raporlayan sınıf.
# Bu sınıf tüm Network Analysis işlemlerinin merkezidir.
# ─────────────────────────────────────────────────────────────────
class GraphAnalyzer:
    """Bağımlılık ilişkilerini modelleyen ve analiz eden sınıf.

    Bu sınıf 3 temel işlem yapar:
        1. build_graph()          → Parser çıktılarından yönlü grafik (DiGraph) oluşturur
        2. find_cycles()          → Grafikteki döngüsel bağımlılıkları tespit eder
        3. calculate_metrics()    → Grafik üzerinden mimari metrikleri hesaplar
        4. get_serializable_data() → Tüm sonuçları API/dashboard için JSON formatında döndürür

    Kullanım:
        >>> analyzer = GraphAnalyzer()
        >>> analyzer.build_graph(parsed_files)       # Grafiği oluştur
        >>> data = analyzer.get_serializable_data()  # Sonuçları al
    """

    def __init__(self):
        """GraphAnalyzer nesnesini başlatır.

        _graph: NetworkX yönlü grafik nesnesi. Her düğüm bir dosya/modül,
                her kenar bir import ilişkisini temsil eder.
        _project_files: Projeye ait dosyaların kümesi (dış kütüphanelerden ayırmak için).
        """
        self._graph: nx.DiGraph = nx.DiGraph()      # Boş bir yönlü grafik oluştur
        self._project_files: Set[str] = set()        # Proje dosyalarını tutacak küme

    # ─────────────────────────────────────────
    # ADIM 1: Grafik Oluşturma
    # Parser'dan gelen dosya bilgilerinden
    # düğüm (node) ve kenar (edge) oluşturur.
    # ─────────────────────────────────────────
    def build_graph(self, parsed_files: List[dict]):
        """Parser (Tree-sitter) çıktılarından bağımlılık grafiğini oluşturur.

        Her dosya bir düğüm (node) olarak eklenir.
        Her import ilişkisi bir kenar (edge) olarak eklenir.
        Yön: kaynak dosya → import edilen dosya şeklindedir.

        Args:
            parsed_files: Parser'ın ürettiği dosya analiz sonuçları listesi.
                Her eleman şu yapıdadır:
                {
                    "file_path": "app/main.py",
                    "language": "python",
                    "imports": [{"module": "app.storage", ...}, ...]
                }
        """
        # Önceki analiz verilerini temizle (yeni analiz için)
        self._graph.clear()

        # Proje dosyalarının listesini oluştur
        # Bu liste, bir import'un proje içi mi yoksa dış kütüphane mi olduğunu belirlemek için kullanılır
        self._project_files = {pf["file_path"] for pf in parsed_files}

        # Her dosyayı düğüm olarak ekle ve import ilişkilerini kenar olarak oluştur
        for pf in parsed_files:
            source = pf["file_path"]   # Kaynak dosya (import yapan dosya)

            # Kaynak dosyayı grafiğe düğüm olarak ekle
            # type="project" → bu dosya projenin bir parçası (dış kütüphane değil)
            self._graph.add_node(source, type="project", language=pf.get("language", "unknown"))

            # Bu dosyanın tüm import'larını tara
            for imp in pf.get("imports", []):
                # Import bilgisinden modül adını çıkar
                module = imp.get("module") if isinstance(imp, dict) else None

                # Geçersiz veya bilinmeyen modülleri atla
                if not module or module == "?":
                    continue

                # Modül adını dosya yoluna dönüştür
                # Örnek: "app.storage" → "app/storage.py"
                target = module.replace(".", "/") + ".py"

                # Hedef dosyanın proje içi mi yoksa dış kütüphane mi olduğunu belirle
                node_type = "project" if target in self._project_files else "external"

                # Hedef düğümü grafiğe ekle (eğer henüz eklenmemişse)
                if not self._graph.has_node(target):
                    self._graph.add_node(target, type=node_type)

                # Kaynak → Hedef yönünde kenar (ok) ekle
                # Bu kenar "source dosyası, target dosyasını import ediyor" anlamına gelir
                self._graph.add_edge(source, target, relation_type="import")

    # ─────────────────────────────────────────
    # ADIM 2: Döngüsel Bağımlılık Tespiti
    # Grafikteki kapalı döngüleri bulur.
    # Örnek döngü: A→B→C→A (A, B'yi; B, C'yi; C, A'yı import ediyor)
    # ─────────────────────────────────────────
    def find_cycles(self) -> List[CycleInfo]:
        """Grafikteki tüm döngüsel bağımlılıkları (circular dependencies) tespit eder.

        NetworkX'in simple_cycles() fonksiyonunu kullanır.
        Bu fonksiyon Tarjan/DFS (Derinlik Öncelikli Arama) algoritmasını temel alır.

        Returns:
            CycleInfo nesnelerinin listesi. Her biri bir döngü zincirini temsil eder.
            Döngü yoksa boş liste döner.
        """
        try:
            # NetworkX'in simple_cycles fonksiyonu ile tüm basit döngüleri bul
            # Basit döngü: aynı düğümden iki kez geçmeyen kapalı yol
            raw_cycles = list(nx.simple_cycles(self._graph))
        except Exception:
            # Grafik boş veya hatalıysa boş liste döndür
            raw_cycles = []

        # Ham döngü verilerini CycleInfo nesnelerine dönüştür
        return [CycleInfo(nodes=cycle) for cycle in raw_cycles]

    # ─────────────────────────────────────────
    # ADIM 3: Mimari Metrik Hesaplama
    # Grafik üzerinden projenin mimari sağlığını
    # ölçen çeşitli metrikleri hesaplar.
    # ─────────────────────────────────────────
    def calculate_metrics(self) -> GraphMetrics:
        """Grafik üzerinden mimari metrikleri hesaplar.

        Hesaplanan metrikler:
            - Grafik Yoğunluğu (Density): Mevcut bağlantı sayısının olası maksimum bağlantı
              sayısına oranı. Yüksek yoğunluk = çok bağlı, karmaşık mimari.
            - Derece Ortalamaları: Her dosyanın ortalama kaç dosyayla bağlantılı olduğu.
            - Güçlü Bağlı Bileşenler (SCC): Karşılıklı erişilebilir düğüm grupları.
              SCC > 1 ise mimari sorunlar olabilir.
            - Kararsızlık Skoru (Instability): Robert C. Martin'in formülü.
              I = Ce / (Ca + Ce) → 0 = stabil, 1 = kararsız.

        Returns:
            GraphMetrics nesnesi (tüm metrikleri içerir).
        """
        G = self._graph
        metrics = GraphMetrics()

        # Grafik boşsa varsayılan (sıfır) metrikleri döndür
        if G.number_of_nodes() == 0:
            return metrics

        # Temel sayımlar
        metrics.total_nodes = G.number_of_nodes()   # Toplam düğüm sayısı
        metrics.total_edges = G.number_of_edges()   # Toplam kenar sayısı

        # Grafik yoğunluğu hesapla (NetworkX fonksiyonu)
        # density = kenar_sayısı / (düğüm_sayısı × (düğüm_sayısı - 1))
        metrics.density = nx.density(G)

        # ── Gelen bağlantı (in-degree) analizi ──
        # In-degree: bir dosyanın kaç farklı dosya tarafından import edildiği
        in_degrees = dict(G.in_degree())
        out_degrees = dict(G.out_degree())

        if in_degrees:
            # Ortalama gelen bağlantı sayısını hesapla
            metrics.avg_in_degree = sum(in_degrees.values()) / len(in_degrees)

            # En çok import edilen dosyayı bul
            max_in_node = max(in_degrees, key=in_degrees.get)
            metrics.max_in_degree = (max_in_node, in_degrees[max_in_node])

        # ── Giden bağlantı (out-degree) analizi ──
        # Out-degree: bir dosyanın kaç farklı dosyayı/kütüphaneyi import ettiği
        if out_degrees:
            # Ortalama giden bağlantı sayısını hesapla
            metrics.avg_out_degree = sum(out_degrees.values()) / len(out_degrees)

            # En çok import yapan dosyayı bul
            max_out_node = max(out_degrees, key=out_degrees.get)
            metrics.max_out_degree = (max_out_node, out_degrees[max_out_node])

        # Güçlü Bağlı Bileşenler (Strongly Connected Components - SCC)
        # Karşılıklı olarak birbirine ulaşılabilen düğüm gruplarını sayar
        # Yüksek SCC sayısı, modüller arası sıkı bağımlılık olduğunu gösterir
        metrics.strongly_connected_components = nx.number_strongly_connected_components(G)

        # ── Kararsızlık Skoru (Instability) ──
        # Robert C. Martin'in Paket Tasarım İlkeleri'nden:
        # I = Ce / (Ca + Ce)
        # Ca (Afferent Coupling)  = gelen bağlantı sayısı (in-degree) → bu dosyayı kullananlar
        # Ce (Efferent Coupling)  = giden bağlantı sayısı (out-degree) → bu dosyanın kullandıkları
        # I = 0 → Tamamen stabil (değiştirilmesi zor, çok dosya buna bağımlı)
        # I = 1 → Tamamen kararsız (kolayca değiştirilebilir, hiçbir şey buna bağımlı değil)
        for node in G.nodes():
            ca = G.in_degree(node)    # Afferent Coupling (gelen)
            ce = G.out_degree(node)   # Efferent Coupling (giden)
            total = ca + ce
            metrics.instability_scores[node] = ce / total if total > 0 else 0.0

        return metrics

    # ─────────────────────────────────────────
    # ADIM 4: Veri Serileştirme
    # Tüm analiz sonuçlarını JSON formatında
    # API ve dashboard için hazırlar.
    # ─────────────────────────────────────────
    def get_serializable_data(self) -> dict:
        """Tüm analiz sonuçlarını JSON'a çevrilebilir sözlük olarak döndürür.

        Bu metot, orchestrator.py tarafından çağrılır ve sonuçlar:
            - API endpoint'leri üzerinden frontend'e gönderilir
            - Dashboard'daki "Network Analysis" sekmesinde görselleştirilir

        Returns:
            {
                "nodes": [...],    → Grafikteki tüm düğümler (dosyalar)
                "edges": [...],    → Grafikteki tüm kenarlar (import ilişkileri)
                "cycles": [...],   → Tespit edilen döngüsel bağımlılıklar
                "metrics": {...}   → Mimari metrikler (yoğunluk, derece, instability vb.)
            }
        """
        # Döngüleri tespit et ve metrikleri hesapla
        cycles = self.find_cycles()
        metrics = self.calculate_metrics()

        # Döngü sayısını metriklere ekle
        metrics.total_cycles = len(cycles)

        # ── Düğüm (Node) listesi oluştur ──
        # Her düğüm bir dosya veya dış kütüphaneyi temsil eder
        nodes = []
        for node, attrs in self._graph.nodes(data=True):
            nodes.append({
                "id": node,                                     # Dosya yolu (benzersiz kimlik)
                "type": attrs.get("type", "unknown"),            # "project" veya "external"
                "in_degree": self._graph.in_degree(node),        # Kaç dosya bunu import ediyor
                "out_degree": self._graph.out_degree(node),      # Bu dosya kaç şeyi import ediyor
            })

        # ── Kenar (Edge) listesi oluştur ──
        # Her kenar bir import ilişkisini temsil eder (kaynak → hedef)
        edges = []
        for src, tgt, attrs in self._graph.edges(data=True):
            edges.append({
                "source_path": src,                                     # Import yapan dosya
                "target_path": tgt,                                     # Import edilen dosya/modül
                "dependency_type": attrs.get("relation_type", "import"), # Bağımlılık tipi
            })

        # Tüm sonuçları birleştirip döndür
        return {
            "nodes": nodes,                              # Düğüm listesi
            "edges": edges,                              # Kenar listesi
            "cycles": [c.to_dict() for c in cycles],     # Döngü bilgileri
            "metrics": metrics.to_dict(),                # Mimari metrikler
        }

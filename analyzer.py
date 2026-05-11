import ast
import os

def get_python_files(directory):
    python_files = []
    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith('.py'):
                python_files.append(os.path.join(root, file))
    return python_files

def extract_imports(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        try:
            tree = ast.parse(f.read())
        except SyntaxError:
            print(f"Hata: {filepath} parse edilemedi (Sözdizimi hatası).")
            return []

    imports = []
    # AST ağacı üzerinde gezin ve tüm düğümleri tek tek incele
    for node in ast.walk(tree):
        # 'import X' şeklindeki kullanımları bul
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append(alias.name)
        # 'from X import Y' şeklindeki kullanımları bul
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imports.append(node.module)
                
    return imports

if __name__ == "__main__":
    project_path = "test_project" 
    files = get_python_files(project_path)
    
    print("=== AST İle Bağımlılık Okuma Başladı ===\n")
    for file in files:
        imports = extract_imports(file)
        
        clean_name = os.path.basename(file)
        
        print(f"Dosya: {clean_name}")
        if imports:
            for imp in imports:
                print(f"  └── Şunu import ediyor: {imp}")
        else:
            print("  └── Bağımlılık yok.")
        print("-" * 30)

"""
parser.py — Tree-sitter destekli kaynak kod ayristirici (v1.1)

PolyMetric `parser_ast.schema.json` v1.1.0 formatinda JSON uretir.
functions[] icin Halstead (n1, N1, n2, N2), return_count ve
executable_lines alanlarini Tree-sitter AST uzerinden hesaplar.
Boylece metrik motoru (ComplexityAnalyzer) AST icinde tekrar gezmek
zorunda kalmadan, parser tarafindan saglanan sayimlarla calisir.

Mevcut kapsam:
  - Python: Tree-sitter ile tam destek (Halstead/ICC alanlari dahil)
  - Java / JavaScript / TypeScript: Engine Lead tarafindan ayni dosyaya
    eklenecek sekilde tasarlandi (NotImplementedError)

Kullanim:
    from app.core.parser import parse_file, build_payload

    payload = build_payload(
        repo_url="https://github.com/example/sample",
        ref="main",
        files=[{"path": "app/main.py", "language": "python", "content": "..."}],
    )
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Iterable

SCHEMA_VERSION = "1.1.0"
PARSER_VERSION = "polymetric-tree-sitter:v0.1.0"
GRAMMAR_VERSION_PYTHON = "tree-sitter-python:bundled"


# Halstead siniflandirma kurallari (Python icin)
# Operand: identifier, sayi, string, sabit literal
# Operator: keyword + punctuation (unnamed leaf token'lar)
_PYTHON_OPERAND_TYPES: set[str] = {
    "identifier",
    "integer",
    "float",
    "string",
    "concatenated_string",
    "true",
    "false",
    "none",
}

_BRANCH_TYPES: set[str] = {
    "if_statement",
    "elif_clause",
    "match_statement",
    "case_clause",
    "except_clause",
    "conditional_expression",
}

_LOOP_TYPES: set[str] = {
    "for_statement",
    "while_statement",
    "for_in_clause",
}


_python_parser: Any = None


def _build_python_parser() -> Any:
    # Tree-sitter import'unu modul yuklendiginde degil ilk kullanimda yapariz
    # boylece tree-sitter kurulmamis ortamlarda diger modul yuklemeleri kirilmaz
    import tree_sitter  # pyright: ignore[reportMissingImports]
    import tree_sitter_python  # pyright: ignore[reportMissingImports]

    language = tree_sitter.Language(tree_sitter_python.language())
    try:
        return tree_sitter.Parser(language)
    except TypeError:
        # Eski tree-sitter API: once parser, sonra dil ata
        parser = tree_sitter.Parser()
        if hasattr(parser, "set_language"):
            parser.set_language(language)
        else:
            parser.language = language
        return parser


def _get_python_parser() -> Any:
    global _python_parser
    if _python_parser is None:
        _python_parser = _build_python_parser()
    return _python_parser


@dataclass
class _HalsteadCounts:
    operators_total: int = 0
    operands_total: int = 0
    operators_unique: set[str] = field(default_factory=set)
    operands_unique: set[str] = field(default_factory=set)


def _node_text(node: Any) -> str:
    return node.text.decode("utf-8", errors="replace")


def _location(node: Any) -> dict:
    start_row, start_col = node.start_point
    end_row, end_col = node.end_point
    return {
        "start_line": start_row + 1,
        "start_col": start_col,
        "end_line": end_row + 1,
        "end_col": end_col,
    }


def _walk_for_halstead(node: Any, counts: _HalsteadCounts) -> None:
    # Yorumlari ve docstring'leri sayma kapsami disinda tut
    if node.type == "comment":
        return

    # Operandler: atomik kod birimleri (identifier, sayi, string vs.)
    if node.type in _PYTHON_OPERAND_TYPES:
        text = _node_text(node)
        counts.operands_total += 1
        counts.operands_unique.add(text)
        return

    # Operatorler: punctuation ve keyword token'lari (unnamed leaf node'lar)
    if not node.is_named and node.child_count == 0:
        text = _node_text(node).strip()
        if text:
            counts.operators_total += 1
            counts.operators_unique.add(text)
        return

    for child in node.children:
        _walk_for_halstead(child, counts)


def _count_branches_loops_returns(node: Any) -> tuple[int, int, int]:
    branch = 1 if node.type in _BRANCH_TYPES else 0
    loop = 1 if node.type in _LOOP_TYPES else 0
    ret = 1 if node.type == "return_statement" else 0
    for child in node.children:
        b, l, r = _count_branches_loops_returns(child)
        branch += b
        loop += l
        ret += r
    return branch, loop, ret


def _count_executable_lines(content: str, start_line: int, end_line: int) -> int:
    # Yorum ve bos satirlar haric calistirilabilir kod satirlarini sayar.
    # Docstring tek bir string node'u oldugu icin operand olarak zaten sayilmiyor;
    # burada da sadece syntactic olarak kod satiri olanlar sayilir.
    lines = content.splitlines()
    upper = min(end_line, len(lines))
    count = 0
    for idx in range(start_line - 1, upper):
        stripped = lines[idx].strip()
        if not stripped or stripped.startswith("#"):
            continue
        count += 1
    return count


def _function_name(node: Any) -> str:
    name_node = node.child_by_field_name("name")
    if name_node is None:
        return "<lambda>"
    return _node_text(name_node)


def _parameters(node: Any) -> list[dict]:
    params: list[dict] = []
    params_node = node.child_by_field_name("parameters")
    if params_node is None:
        return params
    for child in params_node.named_children:
        if child.type == "identifier":
            params.append({"name": _node_text(child), "kind": "positional"})
        elif child.type == "typed_parameter":
            name_node = child.child(0)
            if name_node is not None:
                params.append({"name": _node_text(name_node), "kind": "positional"})
        elif child.type == "default_parameter":
            name_node = child.child_by_field_name("name")
            if name_node is not None:
                params.append({"name": _node_text(name_node), "kind": "keyword"})
        elif child.type == "typed_default_parameter":
            name_node = child.child_by_field_name("name") or child.child(0)
            if name_node is not None:
                params.append({"name": _node_text(name_node), "kind": "keyword"})
        elif child.type == "list_splat_pattern":
            params.append({"name": _node_text(child).lstrip("*"), "kind": "vararg"})
        elif child.type == "dictionary_splat_pattern":
            params.append({"name": _node_text(child).lstrip("*"), "kind": "kwarg"})
    return params


def _build_function_entry(node: Any, content: str, file_id_prefix: str) -> dict:
    counts = _HalsteadCounts()
    body_node = node.child_by_field_name("body")
    if body_node is not None:
        _walk_for_halstead(body_node, counts)
        branch, loop, ret = _count_branches_loops_returns(body_node)
        body_start = body_node.start_point[0] + 1
        body_end = body_node.end_point[0] + 1
        executable_lines = _count_executable_lines(content, body_start, body_end)
    else:
        branch, loop, ret = 0, 0, 0
        executable_lines = 0

    name = _function_name(node)
    return {
        "name": name,
        "qualified_name": name,
        "kind": "function",
        "parameters": _parameters(node),
        "branch_count": branch,
        "loop_count": loop,
        "return_count": ret,
        "executable_lines": executable_lines,
        "unique_operators": len(counts.operators_unique),
        "total_operators": counts.operators_total,
        "unique_operands": len(counts.operands_unique),
        "total_operands": counts.operands_total,
        "location": _location(node),
        "ast_node_id": f"{file_id_prefix}-{node.id}",
    }


def _iter_descendants(root: Any, types: set[str]) -> Iterable[Any]:
    stack = [root]
    while stack:
        node = stack.pop()
        if node.type in types:
            yield node
        for child in node.children:
            stack.append(child)


def _import_entry(node: Any) -> dict:
    text = _node_text(node)
    location = _location(node)
    if node.type == "import_statement":
        # "import logging" -> logging ; "import a, b" -> ilk module'u alir
        tokens = text.split()
        module = tokens[1].split(",")[0] if len(tokens) > 1 else text
        return {
            "kind": "import",
            "module": module,
            "raw_text": text,
            "location": location,
        }
    # import_from_statement: "from app.storage import store"
    tokens = text.split()
    module = tokens[1] if len(tokens) >= 2 and tokens[0] == "from" else "?"
    return {
        "kind": "from_import",
        "module": module,
        "raw_text": text,
        "location": location,
    }


def _class_entry(node: Any, file_id_prefix: str) -> dict:
    name_node = node.child_by_field_name("name")
    name = _node_text(name_node) if name_node is not None else "?"
    methods: list[str] = []
    body_node = node.child_by_field_name("body")
    if body_node is not None:
        for child in body_node.children:
            if child.type == "function_definition":
                method_name_node = child.child_by_field_name("name")
                if method_name_node is not None:
                    methods.append(_node_text(method_name_node))
    return {
        "name": name,
        "qualified_name": name,
        "methods": methods,
        "location": _location(node),
        "ast_node_id": f"{file_id_prefix}-{node.id}",
    }


def parse_python_file(file_path: str, content: str) -> dict:
    parser = _get_python_parser()
    tree = parser.parse(content.encode("utf-8"))
    root = tree.root_node
    file_id_prefix = "f"

    functions = [
        _build_function_entry(fn, content, file_id_prefix)
        for fn in _iter_descendants(root, {"function_definition"})
    ]
    classes = [
        _class_entry(cls, file_id_prefix)
        for cls in _iter_descendants(root, {"class_definition"})
    ]
    imports = [
        _import_entry(imp)
        for imp in _iter_descendants(root, {"import_statement", "import_from_statement"})
    ]

    lines = content.splitlines()
    loc_total = len(lines)
    loc_code = sum(1 for ln in lines if ln.strip() and not ln.strip().startswith("#"))

    return {
        "file_path": file_path,
        "language": "python",
        "encoding": "utf-8",
        "parser": "tree-sitter-python",
        "summary": {
            "loc_total": loc_total,
            "loc_code": loc_code,
            "function_count": len(functions),
            "class_count": len(classes),
            "branch_count": sum(f["branch_count"] for f in functions),
            "loop_count": sum(f["loop_count"] for f in functions),
            "import_count": len(imports),
        },
        "imports": imports,
        "functions": functions,
        "classes": classes,
        "ast": {
            "root_type": root.type,
            "nodes": [
                {
                    "id": f"{file_id_prefix}-root",
                    "type": root.type,
                    "parent_id": None,
                    "named": root.is_named,
                    "location": _location(root),
                }
            ],
        },
    }


def parse_file(file_path: str, content: str, language: str) -> dict:
    if language == "python":
        return parse_python_file(file_path, content)
    raise NotImplementedError(
        f"Tree-sitter parser implementasyonu '{language}' icin Engine Lead "
        f"tarafindan ayni modul icine eklenecek."
    )


def build_payload(
    repo_url: str,
    ref: str,
    files: list[dict],
    commit_hash: str | None = None,
) -> dict:
    """
    Bir veya birden fazla dosyayi parse edip parser_ast.schema.json v1.1.0
    formatinda payload olarak doner.

    files: [{"path": str, "language": str, "content": str}, ...]
    """
    parsed_files: list[dict] = []
    for file in files:
        try:
            parsed_files.append(parse_file(file["path"], file["content"], file["language"]))
        except NotImplementedError:
            # Henuz desteklenmeyen diller atlanir; Engine Lead bunlari hallettiginde
            # otomatik olarak payload'a dahil olur.
            continue

    payload: dict = {
        "schema_version": SCHEMA_VERSION,
        "parser_version": PARSER_VERSION,
        "grammar_version": GRAMMAR_VERSION_PYTHON,
        "repository": {
            "repo_url": repo_url,
            "ref": ref,
            "analyzed_at": datetime.now(timezone.utc)
            .isoformat(timespec="seconds")
            .replace("+00:00", "Z"),
        },
        "files": parsed_files,
    }
    if commit_hash:
        payload["repository"]["commit_hash"] = commit_hash
    return payload

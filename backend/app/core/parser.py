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
    "assert_statement",
    "with_statement",
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
        "grammar_version": get_grammar_version_summary(file.get("language", "") for file in parsed_files),
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


# ---------------------------------------------------------------------------
# Cok dilli parser registry
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class LanguageSpec:
    language: str
    module_name: str
    language_function: str
    parser_name: str
    grammar_version: str
    function_types: set[str]
    class_types: set[str]
    import_types: set[str]
    branch_types: set[str]
    loop_types: set[str]
    return_types: set[str]
    comment_prefixes: tuple[str, ...]


_COMMON_OPERAND_TYPES: set[str] = {
    "identifier",
    "property_identifier",
    "field_identifier",
    "type_identifier",
    "namespace_identifier",
    "integer",
    "float",
    "number",
    "decimal_integer_literal",
    "decimal_floating_point_literal",
    "integer_literal",
    "real_literal",
    "string",
    "string_literal",
    "raw_string_literal",
    "character_literal",
    "char_literal",
    "true",
    "false",
    "null",
    "none",
    "boolean_literal",
}

_NAME_NODE_TYPES = {
    "identifier",
    "property_identifier",
    "field_identifier",
    "type_identifier",
}

_LANGUAGE_SPECS: dict[str, LanguageSpec] = {
    "java": LanguageSpec(
        language="java",
        module_name="tree_sitter_java",
        language_function="language",
        parser_name="tree-sitter-java",
        grammar_version="tree-sitter-java:bundled",
        function_types={"method_declaration", "constructor_declaration"},
        class_types={"class_declaration", "interface_declaration", "enum_declaration", "record_declaration"},
        import_types={"import_declaration"},
        branch_types={"if_statement", "switch_expression", "switch_statement", "catch_clause", "ternary_expression"},
        loop_types={"for_statement", "enhanced_for_statement", "while_statement", "do_statement"},
        return_types={"return_statement"},
        comment_prefixes=("//", "/*", "*"),
    ),
    "javascript": LanguageSpec(
        language="javascript",
        module_name="tree_sitter_javascript",
        language_function="language",
        parser_name="tree-sitter-javascript",
        grammar_version="tree-sitter-javascript:bundled",
        function_types={
            "function_declaration",
            "arrow_function",
            "method_definition",
            "generator_function_declaration",
        },
        class_types={"class_declaration"},
        import_types={"import_statement", "export_statement", "call_expression"},
        branch_types={"if_statement", "switch_statement", "catch_clause", "ternary_expression"},
        loop_types={"for_statement", "for_in_statement", "while_statement", "do_statement"},
        return_types={"return_statement"},
        comment_prefixes=("//", "/*", "*"),
    ),
    "typescript": LanguageSpec(
        language="typescript",
        module_name="tree_sitter_typescript",
        language_function="language_typescript",
        parser_name="tree-sitter-typescript",
        grammar_version="tree-sitter-typescript:bundled",
        function_types={
            "function_declaration",
            "arrow_function",
            "method_definition",
            "method_signature",
        },
        class_types={"class_declaration", "interface_declaration", "enum_declaration", "type_alias_declaration"},
        import_types={"import_statement", "export_statement", "call_expression"},
        branch_types={"if_statement", "switch_statement", "catch_clause", "ternary_expression"},
        loop_types={"for_statement", "for_in_statement", "while_statement", "do_statement"},
        return_types={"return_statement"},
        comment_prefixes=("//", "/*", "*"),
    ),
    "c": LanguageSpec(
        language="c",
        module_name="tree_sitter_c",
        language_function="language",
        parser_name="tree-sitter-c",
        grammar_version="tree-sitter-c:bundled",
        function_types={"function_definition"},
        class_types={"struct_specifier", "union_specifier", "enum_specifier"},
        import_types={"preproc_include"},
        branch_types={"if_statement", "switch_statement", "case_statement", "conditional_expression"},
        loop_types={"for_statement", "while_statement", "do_statement"},
        return_types={"return_statement"},
        comment_prefixes=("//", "/*", "*"),
    ),
    "cpp": LanguageSpec(
        language="cpp",
        module_name="tree_sitter_cpp",
        language_function="language",
        parser_name="tree-sitter-cpp",
        grammar_version="tree-sitter-cpp:bundled",
        function_types={"function_definition", "declaration"},
        class_types={"class_specifier", "struct_specifier", "union_specifier", "enum_specifier"},
        import_types={"preproc_include"},
        branch_types={"if_statement", "switch_statement", "case_statement", "conditional_expression"},
        loop_types={"for_statement", "while_statement", "do_statement", "range_based_for_statement"},
        return_types={"return_statement"},
        comment_prefixes=("//", "/*", "*"),
    ),
    "csharp": LanguageSpec(
        language="csharp",
        module_name="tree_sitter_c_sharp",
        language_function="language",
        parser_name="tree-sitter-c-sharp",
        grammar_version="tree-sitter-c-sharp:bundled",
        function_types={"method_declaration", "constructor_declaration", "local_function_statement"},
        class_types={"class_declaration", "interface_declaration", "struct_declaration", "enum_declaration", "record_declaration"},
        import_types={"using_directive"},
        branch_types={"if_statement", "switch_statement", "switch_expression", "catch_clause", "conditional_expression"},
        loop_types={"for_statement", "foreach_statement", "while_statement", "do_statement"},
        return_types={"return_statement"},
        comment_prefixes=("//", "/*", "*"),
    ),
}

GRAMMAR_VERSIONS: dict[str, str] = {
    "python": GRAMMAR_VERSION_PYTHON,
    **{language: spec.grammar_version for language, spec in _LANGUAGE_SPECS.items()},
}

_parser_cache: dict[str, Any] = {}


def _build_parser_from_module(module_name: str, language_function: str) -> Any:
    import importlib
    import tree_sitter  # pyright: ignore[reportMissingImports]

    module = importlib.import_module(module_name)
    language = tree_sitter.Language(getattr(module, language_function)())
    try:
        return tree_sitter.Parser(language)
    except TypeError:
        parser = tree_sitter.Parser()
        if hasattr(parser, "set_language"):
            parser.set_language(language)
        else:
            parser.language = language
        return parser


def _get_parser_for_spec(spec: LanguageSpec) -> Any:
    if spec.language not in _parser_cache:
        _parser_cache[spec.language] = _build_parser_from_module(spec.module_name, spec.language_function)
    return _parser_cache[spec.language]


def _find_first_descendant(node: Any, types: set[str]) -> Any | None:
    stack = [node]
    while stack:
        current = stack.pop()
        if current.type in types:
            return current
        stack.extend(reversed(current.children))
    return None


def _nearest_parent(node: Any, types: set[str]) -> Any | None:
    current = node.parent
    while current is not None:
        if current.type in types:
            return current
        current = current.parent
    return None


def _generic_function_name(node: Any) -> str:
    name_node = node.child_by_field_name("name")
    if name_node is not None:
        return _node_text(name_node)

    declarator = node.child_by_field_name("declarator")
    if declarator is not None:
        found = _find_first_descendant(declarator, _NAME_NODE_TYPES)
        if found is not None:
            return _node_text(found)

    parent = _nearest_parent(node, {"variable_declarator", "assignment_expression", "pair"})
    if parent is not None:
        parent_name = parent.child_by_field_name("name") or parent.child_by_field_name("left")
        if parent_name is not None:
            found = _find_first_descendant(parent_name, _NAME_NODE_TYPES)
            if found is not None:
                return _node_text(found)

    found = _find_first_descendant(node, _NAME_NODE_TYPES)
    return _node_text(found) if found is not None else "<anonymous>"


def _generic_class_name(node: Any) -> str:
    name_node = node.child_by_field_name("name")
    if name_node is not None:
        return _node_text(name_node)
    found = _find_first_descendant(node, _NAME_NODE_TYPES)
    return _node_text(found) if found is not None else "?"


def _qualified_name(node: Any, base_name: str, class_types: set[str]) -> str:
    names: list[str] = []
    current = node.parent
    while current is not None:
        if current.type in class_types:
            names.append(_generic_class_name(current))
        current = current.parent
    return ".".join(reversed(names)) + "." + base_name if names else base_name


def _generic_parameters(node: Any) -> list[dict]:
    params_node = node.child_by_field_name("parameters")
    if params_node is None:
        return []

    params: list[dict] = []
    seen: set[str] = set()
    for child in _iter_descendants(params_node, _NAME_NODE_TYPES):
        name = _node_text(child)
        if name not in seen:
            seen.add(name)
            params.append({"name": name, "kind": "positional"})
    return params


def _walk_for_halstead_with_spec(node: Any, counts: _HalsteadCounts) -> None:
    if node.type == "comment":
        return
    if node.type in _COMMON_OPERAND_TYPES:
        text = _node_text(node)
        counts.operands_total += 1
        counts.operands_unique.add(text)
        return
    if not node.is_named and node.child_count == 0:
        text = _node_text(node).strip()
        if text:
            counts.operators_total += 1
            counts.operators_unique.add(text)
        return
    for child in node.children:
        _walk_for_halstead_with_spec(child, counts)


def _count_control_flow(node: Any, spec: LanguageSpec) -> tuple[int, int, int]:
    branch = 1 if node.type in spec.branch_types else 0
    loop = 1 if node.type in spec.loop_types else 0
    ret = 1 if node.type in spec.return_types else 0
    for child in node.children:
        b, l, r = _count_control_flow(child, spec)
        branch += b
        loop += l
        ret += r
    return branch, loop, ret


def _body_or_self(node: Any) -> Any:
    return node.child_by_field_name("body") or node


def _build_generic_function_entry(node: Any, content: str, file_id_prefix: str, spec: LanguageSpec) -> dict:
    body_node = _body_or_self(node)
    counts = _HalsteadCounts()
    _walk_for_halstead_with_spec(body_node, counts)
    branch, loop, ret = _count_control_flow(body_node, spec)

    start_line = body_node.start_point[0] + 1
    end_line = body_node.end_point[0] + 1
    name = _generic_function_name(node)
    qualified = _qualified_name(node, name, spec.class_types)

    return {
        "name": qualified,
        "qualified_name": qualified,
        "kind": "function",
        "parameters": _generic_parameters(node),
        "branch_count": branch,
        "loop_count": loop,
        "return_count": ret,
        "executable_lines": _count_executable_lines(content, start_line, end_line),
        "unique_operators": len(counts.operators_unique),
        "total_operators": counts.operators_total,
        "unique_operands": len(counts.operands_unique),
        "total_operands": counts.operands_total,
        "location": _location(node),
        "ast_node_id": f"{file_id_prefix}-{node.id}",
    }


def _build_generic_class_entry(node: Any, file_id_prefix: str, spec: LanguageSpec) -> dict:
    name = _generic_class_name(node)
    methods = [
        _generic_function_name(child)
        for child in _iter_descendants(node, spec.function_types)
    ]
    return {
        "name": name,
        "qualified_name": name,
        "methods": methods,
        "location": _location(node),
        "ast_node_id": f"{file_id_prefix}-{node.id}",
    }


def _extract_quoted_or_bracketed_module(text: str) -> str | None:
    for left, right in (("\"", "\""), ("'", "'"), ("<", ">")):
        if left in text:
            start = text.find(left) + 1
            end = text.find(right, start)
            if end > start:
                return text[start:end]
    return None


def _generic_import_entry(node: Any, spec: LanguageSpec) -> dict | None:
    text = _node_text(node).strip()
    location = _location(node)
    module = "?"
    kind = "import"

    if spec.language in {"javascript", "typescript"}:
        if node.type == "call_expression" and not text.startswith("require"):
            return None
        module = _extract_quoted_or_bracketed_module(text) or "?"
        kind = "require" if text.startswith("require") else "import"
    elif spec.language == "java":
        module = text.removeprefix("import").replace("static", "").strip().rstrip(";").strip()
        kind = "import"
    elif spec.language in {"c", "cpp"}:
        module = _extract_quoted_or_bracketed_module(text) or "?"
        kind = "include"
    elif spec.language == "csharp":
        module = text.removeprefix("using").strip().rstrip(";").strip()
        if "=" in module:
            module = module.split("=", 1)[1].strip()
        kind = "using"

    if not module or module == "?":
        return None
    return {
        "kind": kind,
        "module": module,
        "raw_text": text,
        "location": location,
    }


def _loc_code_for_language(content: str, prefixes: tuple[str, ...]) -> int:
    count = 0
    for line in content.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith(prefixes):
            continue
        count += 1
    return count


def parse_generic_file(file_path: str, content: str, spec: LanguageSpec) -> dict:
    parser = _get_parser_for_spec(spec)
    tree = parser.parse(content.encode("utf-8"))
    root = tree.root_node
    file_id_prefix = spec.language[0]

    functions = [
        _build_generic_function_entry(fn, content, file_id_prefix, spec)
        for fn in _iter_descendants(root, spec.function_types)
    ]
    classes = [
        _build_generic_class_entry(cls, file_id_prefix, spec)
        for cls in _iter_descendants(root, spec.class_types)
    ]

    imports: list[dict] = []
    for imp in _iter_descendants(root, spec.import_types):
        entry = _generic_import_entry(imp, spec)
        if entry is not None:
            imports.append(entry)

    lines = content.splitlines()
    return {
        "file_path": file_path,
        "language": spec.language,
        "encoding": "utf-8",
        "parser": spec.parser_name,
        "summary": {
            "loc_total": len(lines),
            "loc_code": _loc_code_for_language(content, spec.comment_prefixes),
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


def get_grammar_version_summary(languages: Iterable[str] | None = None) -> str:
    selected = set(languages or GRAMMAR_VERSIONS)
    return ", ".join(
        f"{language}={version}"
        for language, version in sorted(GRAMMAR_VERSIONS.items())
        if language in selected
    )


def parse_file(file_path: str, content: str, language: str) -> dict:
    normalized = language.lower()
    if normalized == "python":
        return parse_python_file(file_path, content)
    spec = _LANGUAGE_SPECS.get(normalized)
    if spec is None:
        raise NotImplementedError(f"Tree-sitter parser implementasyonu '{language}' icin yok.")
    return parse_generic_file(file_path, content, spec)

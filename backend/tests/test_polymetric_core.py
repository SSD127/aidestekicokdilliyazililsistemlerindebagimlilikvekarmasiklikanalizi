"""Birim testleri: McCabe sayımı, assert dalı, Halstead effort, risk, test dosyası filtresi."""

import math

from app.core.orchestrator import _halstead_effort, _is_test_file, _mccabe
from app.core.parser import parse_file
from app.core.risk import calculate_risk_level


def test_simple_function_mccabe_is_one() -> None:
    src = "def f():\n    return 1\n"
    parsed = parse_file("m.py", src, "python")
    fn = parsed["functions"][0]
    assert fn["branch_count"] == 0
    assert fn["loop_count"] == 0
    assert _mccabe(fn["branch_count"], fn["loop_count"]) == 1


def test_if_increases_cyclomatic_complexity() -> None:
    src = "def g(x):\n    if x:\n        return 1\n    return 2\n"
    parsed = parse_file("m.py", src, "python")
    fn = parsed["functions"][0]
    assert _mccabe(fn["branch_count"], fn["loop_count"]) == 2


def test_assert_increases_branch_count_vs_plain() -> None:
    plain = parse_file("a.py", "def f():\n    pass\n", "python")["functions"][0]
    with_assert = parse_file("b.py", "def g():\n    assert True\n", "python")["functions"][0]
    assert with_assert["branch_count"] > plain["branch_count"]


def test_halstead_effort_matches_formula() -> None:
    n1, N1, n2, N2 = 2, 4, 2, 4
    n = n1 + n2
    N = N1 + N2
    expected = (n1 / 2.0) * (N2 / n2) * (N * math.log2(n))
    assert math.isclose(_halstead_effort(n1, N1, n2, N2), expected)


def test_calculate_risk_level_low_for_trivial_function() -> None:
    assert calculate_risk_level(1, 0.0) == "low"


def test_is_test_file_patterns() -> None:
    assert _is_test_file("tests/test_foo.py") is True
    assert _is_test_file("pkg/widget_test.py") is True
    assert _is_test_file("src/app.py") is False
    assert _is_test_file("tests/conftest.py") is False

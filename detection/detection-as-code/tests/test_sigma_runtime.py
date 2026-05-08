"""Unit tests for the Sigma evaluator — covering modifiers, list-OR semantics,
condition operators, wildcards, and the negative-filter pattern."""
from __future__ import annotations

import pytest

from detection_as_code.sigma_runtime import _eval_condition, _selection_matches, matches


def test_field_equals_case_insensitive() -> None:
    block = {"Image": "POWERSHELL.EXE"}
    assert _selection_matches(block, {"Image": "powershell.exe"})


def test_field_endswith() -> None:
    block = {"Image|endswith": "\\powershell.exe"}
    assert _selection_matches(block, {"Image": "C:\\Windows\\System32\\powershell.exe"})
    assert not _selection_matches(block, {"Image": "C:\\malware\\powershell.exe.dat"})


def test_field_contains() -> None:
    block = {"CommandLine|contains": " -enc "}
    assert _selection_matches(block, {"CommandLine": "powershell.exe -enc SQBFAFgA"})
    assert not _selection_matches(block, {"CommandLine": "powershell.exe -encoded"})


def test_field_startswith() -> None:
    block = {"User|startswith": "DC01\\"}
    assert _selection_matches(block, {"User": "DC01\\administrator"})
    assert not _selection_matches(block, {"User": "FINANCE\\administrator"})


def test_field_regex() -> None:
    block = {"CommandLine|re": r" -e(c|nc(odedcommand)?)? "}
    assert _selection_matches(block, {"CommandLine": "ps -enc xxx"})
    assert _selection_matches(block, {"CommandLine": "ps -EncodedCommand xxx"})
    assert not _selection_matches(block, {"CommandLine": "ps -ExecutionPolicy"})


def test_list_value_is_or() -> None:
    block = {"CommandLine|contains": [" -enc ", " -EncodedCommand "]}
    assert _selection_matches(block, {"CommandLine": "ps -enc xxx"})
    assert _selection_matches(block, {"CommandLine": "ps -EncodedCommand xxx"})
    assert not _selection_matches(block, {"CommandLine": "ps -nop"})


def test_missing_field_is_false() -> None:
    block = {"Image": "powershell.exe"}
    assert not _selection_matches(block, {"User": "admin"})


def test_condition_simple_selection() -> None:
    assert _eval_condition("selection", {"selection": True})
    assert not _eval_condition("selection", {"selection": False})


def test_condition_and_or() -> None:
    sels = {"a": True, "b": False, "c": True}
    assert _eval_condition("a and c", sels)
    assert not _eval_condition("a and b", sels)
    assert _eval_condition("a or b", sels)
    assert not _eval_condition("b or b", sels)


def test_condition_not() -> None:
    assert _eval_condition("not selection", {"selection": False})
    assert not _eval_condition("not selection", {"selection": True})


def test_condition_parens() -> None:
    sels = {"a": True, "b": False, "c": True}
    assert _eval_condition("a and (b or c)", sels)
    assert not _eval_condition("(a and b) or (b and c)", sels)


def test_condition_wildcard_one_of() -> None:
    sels = {"selection_a": False, "selection_b": True, "selection_c": False}
    assert _eval_condition("1 of selection_*", sels)


def test_condition_wildcard_all_of() -> None:
    sels = {"sel_a": True, "sel_b": True}
    assert _eval_condition("all of sel_*", sels)
    sels2 = {"sel_a": True, "sel_b": False}
    assert not _eval_condition("all of sel_*", sels2)


def test_condition_negative_filter_pattern() -> None:
    """Sigma's classic 'selection and not filter' pattern."""
    sels = {"selection": True, "filter_local": False}
    assert _eval_condition("selection and not filter_local", sels)
    sels2 = {"selection": True, "filter_local": True}
    assert not _eval_condition("selection and not filter_local", sels2)


def test_full_rule_matches() -> None:
    rule = {
        "detection": {
            "selection": {
                "Image|endswith": "\\powershell.exe",
                "CommandLine|contains": " -enc ",
            },
            "condition": "selection",
        },
    }
    event = {
        "Image": "C:\\Windows\\System32\\powershell.exe",
        "CommandLine": "powershell.exe -enc SQBFAFgA",
    }
    assert matches(rule, event)


def test_unknown_modifier_raises() -> None:
    with pytest.raises(ValueError, match="unsupported sigma modifier"):
        _selection_matches({"x|whatever": "y"}, {"x": "y"})


def test_unknown_selection_in_condition_raises() -> None:
    with pytest.raises(ValueError, match="unknown selection"):
        _eval_condition("missing_selection", {"selection": True})

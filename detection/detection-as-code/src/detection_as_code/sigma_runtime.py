"""Minimal in-process Sigma evaluator for fixture-based rule testing.

The real production target is a SIEM (Splunk / ES / KQL via pysigma backends).
This evaluator is intentionally narrow: it parses a Sigma rule's `detection`
block and evaluates it against in-memory event dicts so the purple-team runner
can execute the same rule body against a known fixture without standing up a
SIEM container.

Supported:
- selection blocks with `field=value`, `field|contains`, `field|startswith`,
  `field|endswith`, `field|re` modifiers
- list-valued expected (any-match)
- conditions: `selection`, `not <name>`, `<a> and <b>`, `<a> or <b>`, parens,
  `1 of <prefix>*`, `all of <prefix>*`

Not supported (would 400 in real Sigma processing too): aggregation, near, count,
correlation. Add as the corpus needs them.
"""
from __future__ import annotations

import re
from typing import Any


def matches(rule: dict[str, Any], event: dict[str, Any]) -> bool:
    """Return True if the rule's detection logic matches the event."""
    detection = rule["detection"]
    selection_results: dict[str, bool] = {
        name: _selection_matches(block, event)
        for name, block in detection.items()
        if name != "condition"
    }
    return _eval_condition(detection["condition"], selection_results)


def _selection_matches(block: dict[str, Any], event: dict[str, Any]) -> bool:
    """A selection block is a dict of field-pattern -> expected. AND across keys."""
    for key, expected in block.items():
        if "|" in key:
            field, modifier = key.split("|", 1)
        else:
            field, modifier = key, "equals"
        actual = event.get(field, None)
        if not _field_matches(actual, modifier, expected):
            return False
    return True


def _field_matches(actual: Any, modifier: str, expected: Any) -> bool:
    """Apply a Sigma modifier between actual (event value) and expected (rule value).
    `expected` may be a list — in that case OR over the elements."""
    if isinstance(expected, list):
        return any(_field_matches(actual, modifier, e) for e in expected)
    if actual is None:
        return False

    actual_s = str(actual).lower()
    expected_s = str(expected).lower()

    if modifier == "equals":
        # Sigma equality is case-insensitive for strings, exact for numbers.
        if isinstance(actual, (int, float)) and isinstance(expected, (int, float)):
            return actual == expected
        return actual_s == expected_s
    if modifier == "contains":
        return expected_s in actual_s
    if modifier == "startswith":
        return actual_s.startswith(expected_s)
    if modifier == "endswith":
        return actual_s.endswith(expected_s)
    if modifier == "re":
        return bool(re.search(expected_s, actual_s))
    raise ValueError(f"unsupported sigma modifier: {modifier!r}")


# ---------------------------------------------------------------------------
# Condition expression parser (recursive descent)
# ---------------------------------------------------------------------------

_TOKEN_RE = re.compile(r"\(|\)|\bnot\b|\band\b|\bor\b|\b1 of\b|\ball of\b|[A-Za-z_][\w*]*")


def _tokenize(expr: str) -> list[str]:
    return _TOKEN_RE.findall(expr)


def _eval_condition(expr: str, selections: dict[str, bool]) -> bool:
    tokens = _tokenize(expr)
    parser = _ConditionParser(tokens, selections)
    result = parser.parse_or()
    if parser.pos != len(tokens):
        raise ValueError(f"unparsed tokens in condition: {tokens[parser.pos:]}")
    return result


class _ConditionParser:
    def __init__(self, tokens: list[str], selections: dict[str, bool]) -> None:
        self.tokens = tokens
        self.pos = 0
        self.selections = selections

    def _peek(self) -> str | None:
        return self.tokens[self.pos] if self.pos < len(self.tokens) else None

    def _consume(self) -> str:
        tok = self.tokens[self.pos]
        self.pos += 1
        return tok

    def parse_or(self) -> bool:
        left = self.parse_and()
        while self._peek() == "or":
            self._consume()
            right = self.parse_and()
            left = left or right
        return left

    def parse_and(self) -> bool:
        left = self.parse_not()
        while self._peek() == "and":
            self._consume()
            right = self.parse_not()
            left = left and right
        return left

    def parse_not(self) -> bool:
        if self._peek() == "not":
            self._consume()
            return not self.parse_not()
        return self.parse_atom()

    def parse_atom(self) -> bool:
        tok = self._peek()
        if tok == "(":
            self._consume()
            inner = self.parse_or()
            if self._peek() != ")":
                raise ValueError("missing )")
            self._consume()
            return inner
        if tok in ("1 of", "all of"):
            self._consume()
            prefix_tok = self._consume()  # e.g. "selection_*"
            return self._wildcard(prefix_tok, all_required=tok == "all of")
        # Plain selection name.
        name = self._consume()
        if name not in self.selections:
            raise ValueError(
                f"condition references unknown selection {name!r}; "
                f"known: {sorted(self.selections)}"
            )
        return self.selections[name]

    def _wildcard(self, pattern: str, *, all_required: bool) -> bool:
        if not pattern.endswith("*"):
            raise ValueError(f"expected wildcard pattern ending in *, got {pattern!r}")
        prefix = pattern[:-1]
        matching = [v for k, v in self.selections.items() if k.startswith(prefix)]
        if not matching:
            raise ValueError(f"no selections match pattern {pattern!r}")
        return all(matching) if all_required else any(matching)

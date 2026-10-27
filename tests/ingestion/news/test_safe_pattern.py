"""NP5a: the one pattern grammar (taken from the company list, widened by a few literals for the shipped phrases)."""

from __future__ import annotations

import re
import time

import pytest

from fno.ingestion.news.safe_pattern import compile_safe, is_safe_pattern
from fno.ingestion.news.sources.loader import SourceRulesError, build_source_rules, load_source_rules

SAFE = [
    "Zzfoo Bar", r"Zzfoo Bar\w*", "Zzbar (?:Lifespaces?|Holdings)\\w*", "advertorial", "sponsored (?:content|post)",
    r"Zz Rank #", r"Target Price \(Mid\)", "Q3: results/outlook", "A\\.B Ltd", "ZZ&Q (?:Finance|Tech)\\w*", "x" * 120,
]  # fmt: skip
UNSAFE = [
    "", "x" * 121, ".*.*Z", r"\w*\w*!", "(a+)+b", "(a|b)*c", "a|b", "[ab]", "a*", "a{2}", "(?=a)b", r"\1", "(?:a|b)?",
    "(?:a|b)(?:c|d)(?:e|f)", "a?a?a?a?a?", "(?:a|a)" * 23 + "x", r"\w*x", r"\d", "a.b", "(unclosed", "a\\", "%", "(a)",
]  # fmt: skip


@pytest.mark.parametrize("pattern", SAFE)
def test_a_pattern_in_the_grammar_is_safe_and_compiles(pattern):
    assert is_safe_pattern(pattern) and compile_safe(pattern).flags & re.IGNORECASE


@pytest.mark.parametrize("pattern", UNSAFE)
def test_anything_else_is_refused(pattern):
    assert not is_safe_pattern(pattern)
    with pytest.raises(ValueError):
        compile_safe(pattern)


def test_the_literals_added_for_the_shipped_phrases_match_literally():
    assert compile_safe(r"Zz Rank #").search("see zz rank # 2 today")
    assert compile_safe(r"Target Price \(Mid\)").search("Target price (mid) raised")
    assert not compile_safe(r"Target Price \(Mid\)").search("Target price mid")


def test_the_heaviest_pattern_the_grammar_allows_stays_fast_on_a_long_text():
    group = "(?:" + "|".join(["a" * 8] * 5) + ")"
    heavy = group + group + r"a?a?b\w*"
    assert is_safe_pattern(heavy)
    start = time.monotonic()
    compile_safe(heavy).search("a" * 50_000)
    assert time.monotonic() - start < 2


def test_every_shipped_promotional_phrase_is_in_the_grammar_and_the_shipped_file_loads():
    """judge 90 F1: two of the eight phrases did not fit the first grammar; the loader would have refused the file."""
    rules = load_source_rules()
    assert rules.promotional.text and all(is_safe_pattern(p) for p in rules.promotional.text)


def test_the_loader_refuses_a_promotional_phrase_outside_the_grammar():
    base = {"domains": {"a.com": {"tier": "tier1"}}}
    with pytest.raises(SourceRulesError, match="not a safe pattern"):
        build_source_rules({**base, "promotional": {"text": [".*.*.*x"]}})

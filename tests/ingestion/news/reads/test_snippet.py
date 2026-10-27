"""NP10: the page snippet is a short, deterministic piece of the article body, in its own field, and nowhere else."""

from __future__ import annotations

import json

import pytest

from fno.ingestion.news.reads.extract import extract
from fno.ingestion.news.reads.read_file import build_read, parse_read
from fno.ingestion.news.reads.snippet import sentences, summary_extract

LONG = "Zzalpha Holdings reported a net profit of Rs. 500 crore for the quarter. Mr. Zz Kumar said it was strong! " + (
    "Another full sentence follows here. " * 40
)


def page(ld: dict) -> bytes:
    return f'<html><head><script type="application/ld+json">{json.dumps(ld)}</script></head></html>'.encode()


def article(body: str, **more) -> dict:
    return {"@type": "NewsArticle", "articleBody": body, **more}


def test_only_the_first_three_sentences_are_kept():
    text = "One is here. Two is here. Three is here. Four is here. Five is here."
    assert summary_extract(text) == "One is here. Two is here. Three is here."


def test_the_snippet_never_passes_the_character_cap_and_ends_at_a_word_boundary():
    snippet = summary_extract("abcdef " * 400)
    assert len(snippet) <= 600 and snippet.endswith(" abcdef") and snippet == snippet.rstrip()
    assert len(summary_extract(LONG)) <= 600


def test_a_full_stop_after_rs_or_a_title_before_a_number_or_a_lower_case_word_is_not_a_sentence_end():
    found = sentences(" ".join(LONG.split()))
    assert found[0].endswith("for the quarter.") and found[1].startswith("Mr. Zz Kumar said it was strong!")
    assert sentences("It cost approx. nine crore. Then it fell.") == ["It cost approx. nine crore.", "Then it fell."]
    assert sentences("Pay Ltd. Zz now. It ends here.")[0] == "Pay Ltd. Zz now."
    assert sentences("Profit hit Rs. 5 crore. Next.")[0] == "Profit hit Rs. 5 crore."


def test_tags_and_entities_are_stripped_and_control_characters_collapsed():
    assert (
        summary_extract("<p>Acme &amp; Zz\x00 grew.</p><script>x</script> Next one.") == "Acme & Zz grew. x Next one."
    )


def test_a_paywalled_page_and_a_meta_only_page_keep_no_snippet():
    assert extract(page(article(LONG, isAccessibleForFree=False))).summary_extract == ""
    meta = b'<html><head><meta property="og:site_name" content="Zz Outlet"></head></html>'
    assert extract(meta).summary_extract == ""
    assert extract(page(article(LONG))).summary_extract.startswith("Zzalpha Holdings reported")


def test_a_short_partial_page_gives_its_whole_short_body_under_the_same_caps():
    facts = extract(page(article("A short body only. It has two sentences.")))
    read = build_read("k" * 64, "pub.example", facts)
    assert read.access == "partial" and read.summary_extract == "A short body only. It has two sentences."


def test_the_same_page_gives_the_same_snippet_and_the_same_file_bytes():
    first = build_read("k" * 64, "pub.example", extract(page(article(LONG)))).to_bytes()
    assert first == build_read("k" * 64, "pub.example", extract(page(article(LONG)))).to_bytes()


def test_the_snippet_is_its_own_field_the_body_hash_and_length_are_unchanged_and_nothing_prints_it():
    facts = extract(page(article(LONG)))
    read = build_read("k" * 64, "pub.example", facts)
    document = json.loads(read.to_bytes())
    assert document["summary_extract"] == read.summary_extract and document["format"] == 2
    assert document["body_chars"] == len(" ".join(LONG.split())) and len(document["body_sha256"]) == 64
    assert read.summary_extract not in repr(read) and read.summary_extract not in repr(facts)


def test_a_file_of_the_old_format_or_with_an_unknown_key_is_refused():
    document = json.loads(build_read("k" * 64, "pub.example", extract(page(article(LONG)))).to_bytes())
    parse_read(json.dumps(document).encode())
    for bad in (
        {**document, "format": 1},
        {**document, "extra": 1},
        {k: v for k, v in document.items() if k != "summary_extract"},
    ):
        with pytest.raises(ValueError):
            parse_read(json.dumps(bad).encode())


def test_the_snippet_is_in_the_read_file_only_never_in_a_report_a_manifest_a_receipt_or_the_rest_of_the_drive(tmp_path):
    """NP10 privacy: the page text is private Drive content. A planted phrase must be found in exactly one place."""
    from fno.ingestion.news.pages import model
    from tests.ingestion.news.reads.helpers import HTML, Page, World

    secret = "Zzsecretphrase opens this planted page. A second planted sentence follows."
    page = HTML.replace(b"word " * 100, secret.encode())
    world = World(tmp_path)
    world.add_publisher(1)
    world.fetcher.fetch = lambda url, seconds=None: Page(model.OK, url, "text/html", body=page)
    report = world.read()
    holders = [p for p in tmp_path.rglob("*") if p.is_file() and b"Zzsecretphrase" in p.read_bytes()]
    assert [p.name for p in holders] == [world.read_files()[0].rsplit("/", 1)[-1]]
    for text in (report.line(), repr(report), str(report.__dict__)):
        assert "Zzsecretphrase" not in text

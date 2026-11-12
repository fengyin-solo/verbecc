from typing import Generator

import pytest

from verbecc import VerbCatalog
from verbecc.core.defs.types.data.verb_catalog_entry import VerbCatalogEntry
from verbecc.core.defs.types.data.verb_match_reason import VerbMatchReason
from verbecc.core.defs.types.lang_code import LangCodeISO639_1 as Lang
from verbecc.core.parsers.verbs_parser import VerbsParser

ALL_LANGS: list[Lang] = [
    Lang.ca,
    Lang.es,
    Lang.fr,
    Lang.it,
    Lang.pt,
    Lang.ro,
]

REASON_PRIORITY: list[VerbMatchReason] = [
    VerbMatchReason.exact,
    VerbMatchReason.exact_no_accents,
    VerbMatchReason.prefix,
    VerbMatchReason.substring,
    VerbMatchReason.translation_en,
]


def _best_rank(reasons: list[VerbMatchReason]) -> int:
    return min(REASON_PRIORITY.index(reason) for reason in reasons)


def _find_entry(
    entries: list[VerbCatalogEntry], infinitive: str
) -> VerbCatalogEntry:
    return next(entry for entry in entries if entry.infinitive == infinitive)


@pytest.fixture(scope="module")
def catalog() -> Generator[VerbCatalog, None, None]:
    yield VerbCatalog(Lang.fr)


@pytest.fixture(scope="module")
def catalogs() -> dict[Lang, VerbCatalog]:
    return {lang: VerbCatalog(lang) for lang in ALL_LANGS}


@pytest.mark.parametrize("query", ["", "   ", "\t"])
def test_empty_query_returns_empty_list(
    catalog: VerbCatalog, query: str
) -> None:
    assert catalog.search(query) == []


def test_exact_match_returns_verb_metadata(catalog: VerbCatalog) -> None:
    entry = catalog.search("manger")[0]
    assert entry.infinitive == "manger"
    assert entry.template == "man:ger"
    assert entry.translation_en == "eat"
    assert entry.reasons == [VerbMatchReason.exact]


def test_exact_match_is_case_insensitive(catalog: VerbCatalog) -> None:
    assert catalog.search("Manger") == catalog.search("manger")
    assert catalog.search("MANGER")[0].reasons == [VerbMatchReason.exact]


def test_accented_exact_match(catalog: VerbCatalog) -> None:
    results = catalog.search("abâtardir")
    assert results[0].infinitive == "abâtardir"
    assert results[0].reasons == [VerbMatchReason.exact]


def test_unaccented_query_matches_accented_verb(catalog: VerbCatalog) -> None:
    results = catalog.search("abatardir")
    assert results[0].infinitive == "abâtardir"
    assert results[0].reasons == [VerbMatchReason.exact_no_accents]


def test_prefix_match(catalog: VerbCatalog) -> None:
    results = catalog.search("mang")
    prefix_entries = [
        entry
        for entry in results
        if VerbMatchReason.prefix in entry.reasons
    ]
    assert [entry.infinitive for entry in prefix_entries] == [
        "mangeotter",
        "manger",
    ]


def test_internal_substring_match(catalog: VerbCatalog) -> None:
    results = catalog.search("mange")
    substring_entries = {
        entry.infinitive: entry
        for entry in results
        if VerbMatchReason.substring in entry.reasons
    }
    assert "démanger" in substring_entries
    assert "remanger" in substring_entries
    for infinitive in substring_entries:
        assert not infinitive.startswith("mange")


def test_english_translation_match(catalog: VerbCatalog) -> None:
    results = catalog.search("eat")
    manger = _find_entry(results, "manger")
    assert VerbMatchReason.translation_en in manger.reasons

    results_uppercase = catalog.search("EAT")
    assert any(entry.infinitive == "manger" for entry in results_uppercase)


def test_duplicate_hits_are_merged_into_one_entry(
    catalog: VerbCatalog,
) -> None:
    results = catalog.search("poison")
    infinitives = [entry.infinitive for entry in results]
    assert infinitives.count("empoisonner") == 1
    empoisonner = _find_entry(results, "empoisonner")
    assert empoisonner.reasons == [
        VerbMatchReason.substring,
        VerbMatchReason.translation_en,
    ]


def test_results_are_deduplicated_by_verb(catalog: VerbCatalog) -> None:
    for query in ("a", "er", "manger", "eat", "poison"):
        infinitives = [
            entry.infinitive
            for entry in catalog.search(
                query, limit=VerbCatalog.MAX_SEARCH_LIMIT
            )
        ]
        assert len(infinitives) == len(set(infinitives))


def test_tier_priority_ordering(catalog: VerbCatalog) -> None:
    results = catalog.search("manger")
    ranks = [_best_rank(entry.reasons) for entry in results]
    assert ranks == sorted(ranks)
    assert results[0].infinitive == "manger"
    assert results[0].reasons == [VerbMatchReason.exact]


def test_same_tier_is_sorted_by_infinitive(catalog: VerbCatalog) -> None:
    results = catalog.search("man")
    prefix_infinitives = [
        entry.infinitive
        for entry in results
        if entry.reasons[0] == VerbMatchReason.prefix
    ]
    assert prefix_infinitives == sorted(prefix_infinitives)
    assert len(prefix_infinitives) > 1


def test_limit_caps_result_count(catalog: VerbCatalog) -> None:
    assert len(catalog.search("a", limit=3)) == 3


def test_default_limit(catalog: VerbCatalog) -> None:
    results = catalog.search("a")
    assert len(results) == VerbCatalog.DEFAULT_SEARCH_LIMIT


def test_max_limit_is_allowed(catalog: VerbCatalog) -> None:
    results = catalog.search("a", limit=VerbCatalog.MAX_SEARCH_LIMIT)
    assert len(results) == VerbCatalog.MAX_SEARCH_LIMIT


@pytest.mark.parametrize("bad_limit", [0, -1, 101, 1000])
def test_invalid_limit_raises_value_error(
    catalog: VerbCatalog, bad_limit: int
) -> None:
    with pytest.raises(ValueError):
        catalog.search("a", limit=bad_limit)


def test_unknown_query_returns_empty_without_prediction(
    catalog: VerbCatalog,
) -> None:
    # The catalog is read-only and must never invoke ML template prediction:
    # an unknown verb yields no results instead of a predicted Verb.
    assert catalog.search("zzqqxx-not-a-real-verb") == []


def test_index_is_built_once_and_covers_every_verb(
    catalog: VerbCatalog,
) -> None:
    parsed = VerbsParser(Lang.fr).parse()
    assert len(catalog) == len(parsed)
    results = catalog.search("a", limit=VerbCatalog.MAX_SEARCH_LIMIT)
    for entry in results:
        assert entry.infinitive != ""
        assert entry.template != ""
        assert isinstance(entry.translation_en, str)


@pytest.mark.parametrize("lang", ALL_LANGS)
def test_catalog_loads_for_all_six_languages(
    catalogs: dict[Lang, VerbCatalog],
    lang: Lang,
) -> None:
    catalog = catalogs[lang]
    parsed = VerbsParser(lang).parse()
    assert len(catalog) == len(parsed)

    first_verb = parsed.infinitives[0]
    results = catalog.search(first_verb[:3])
    assert results
    entry = _find_entry(results, first_verb)
    assert VerbMatchReason.prefix in entry.reasons
    assert entry.template != ""

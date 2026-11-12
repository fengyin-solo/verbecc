import pytest
from typing import Generator

from verbecc import BatchConjugator
from verbecc import CompleteConjugator
from verbecc.core.conjugator.batch_conjugation_result import (
    BatchConjugationResult,
)
from verbecc.core.defs.types.conjugation.complete_conjugation import (
    CompleteConjugation,
)
from verbecc.core.defs.types.exceptions import VerbNotFoundError
from verbecc.core.defs.types.lang_code import LangCodeISO639_1 as Lang


@pytest.fixture(scope="module")
def bcg() -> Generator[BatchConjugator, None, None]:
    yield BatchConjugator(lang=Lang.fr)


def test_batch_conjugator_reuses_single_language_instance(
    bcg: BatchConjugator,
) -> None:
    shared = bcg.get_conjugator()
    assert isinstance(shared, CompleteConjugator)
    bcg.conjugate(["parler"])
    assert bcg.get_conjugator() is shared


def test_batch_all_success_aligns_strictly_with_input(bcg: BatchConjugator) -> None:
    verbs = ["parler", "manger", "venir"]
    results = bcg.conjugate(verbs)

    assert len(results) == len(verbs)
    for index, (result, verb) in enumerate(zip(results, verbs)):
        assert isinstance(result, BatchConjugationResult)
        assert result.get_index() == index
        assert result.get_indices() == [index]
        assert result.get_infinitive() == verb
        assert result.is_success()
        assert not result.is_error()
        assert result.get_error_type() is None
        assert result.get_error_message() is None
        conjugation = result.get_conjugation()
        assert isinstance(conjugation, CompleteConjugation)
        assert conjugation.get_verb_info().infinitive == verb


def test_batch_empty_input_returns_empty_list(bcg: BatchConjugator) -> None:
    assert bcg.conjugate([]) == []
    assert bcg.conjugate([], continue_on_error=True, deduplicate=True) == []


def test_batch_default_stops_and_reraises_at_first_error(
    bcg: BatchConjugator, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls: list[str] = []
    shared_conjugator = bcg.get_conjugator()
    original_conjugate = shared_conjugator.conjugate

    def spy(infinitive: str, conjugate_pronouns: bool = True) -> CompleteConjugation:
        calls.append(infinitive)
        return original_conjugate(infinitive, conjugate_pronouns=conjugate_pronouns)

    monkeypatch.setattr(shared_conjugator, "conjugate", spy)

    with pytest.raises(VerbNotFoundError):
        bcg.conjugate(["parler", "s'être", "manger"])

    assert calls == ["parler", "s'être"]


def test_batch_continue_on_error_records_failure_in_place(
    bcg: BatchConjugator, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls: list[str] = []
    shared_conjugator = bcg.get_conjugator()
    original_conjugate = shared_conjugator.conjugate

    def spy(infinitive: str, conjugate_pronouns: bool = True) -> CompleteConjugation:
        calls.append(infinitive)
        return original_conjugate(infinitive, conjugate_pronouns=conjugate_pronouns)

    monkeypatch.setattr(shared_conjugator, "conjugate", spy)

    verbs = ["parler", "s'être", "manger"]
    results = bcg.conjugate(verbs, continue_on_error=True)

    assert calls == verbs
    assert [result.get_index() for result in results] == [0, 1, 2]
    assert [result.get_infinitive() for result in results] == verbs

    assert results[0].is_success()
    assert results[0].get_conjugation() is not None

    failed = results[1]
    assert failed.is_error()
    assert not failed.is_success()
    assert failed.get_conjugation() is None
    assert failed.get_error_type() == VerbNotFoundError.__name__
    assert failed.get_error_message() is not None
    assert "reflexive" in failed.get_error_message()
    assert failed.get_indices() == [1]

    assert results[2].is_success()
    assert results[2].get_conjugation() is not None


def test_batch_all_failures_keep_structure_and_order(bcg: BatchConjugator) -> None:
    verbs = ["s'être", "se pleuvoir"]
    results = bcg.conjugate(verbs, continue_on_error=True)

    assert len(results) == 2
    assert [result.get_index() for result in results] == [0, 1]
    assert all(result.is_error() for result in results)
    assert [result.get_error_type() for result in results] == [
        VerbNotFoundError.__name__,
        VerbNotFoundError.__name__,
    ]
    assert all(result.get_conjugation() is None for result in results)


def test_batch_without_deduplicate_conjugates_every_position(
    bcg: BatchConjugator,
) -> None:
    results = bcg.conjugate(["parler", "parler"])

    assert len(results) == 2
    assert [result.get_index() for result in results] == [0, 1]
    assert [result.get_indices() for result in results] == [[0], [1]]
    assert all(result.is_success() for result in results)
    assert results[0].get_conjugation() == results[1].get_conjugation()


def test_batch_deduplicate_keeps_first_occurrence_and_maps_all_positions(
    bcg: BatchConjugator, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls: list[str] = []
    shared_conjugator = bcg.get_conjugator()
    original_conjugate = shared_conjugator.conjugate

    def spy(infinitive: str, conjugate_pronouns: bool = True) -> CompleteConjugation:
        calls.append(infinitive)
        return original_conjugate(infinitive, conjugate_pronouns=conjugate_pronouns)

    monkeypatch.setattr(shared_conjugator, "conjugate", spy)

    verbs = ["parler", "Parler", "manger", "PARLER", "parler"]
    results = bcg.conjugate(verbs, deduplicate=True)

    # each normalized input is conjugated only once
    assert calls == ["parler", "manger"]

    assert len(results) == 2
    assert [result.get_index() for result in results] == [0, 2]

    first = results[0]
    assert first.get_infinitive() == "parler"
    assert first.get_indices() == [0, 1, 3, 4]
    assert first.is_success()

    second = results[1]
    assert second.get_infinitive() == "manger"
    assert second.get_indices() == [2]
    assert second.is_success()

    # every original position maps to exactly one unique result
    position_map: dict[int, BatchConjugationResult] = {}
    for result in results:
        for original_index in result.get_indices():
            position_map[original_index] = result
    assert sorted(position_map.keys()) == list(range(len(verbs)))


def test_batch_deduplicate_with_errors_maps_duplicate_failures(
    bcg: BatchConjugator,
) -> None:
    results = bcg.conjugate(
        ["s'être", "parler", "S'ÊTRE"],
        continue_on_error=True,
        deduplicate=True,
    )

    assert len(results) == 2
    assert [result.get_index() for result in results] == [0, 1]

    failed = results[0]
    assert failed.get_infinitive() == "s'être"
    assert failed.is_error()
    assert failed.get_error_type() == VerbNotFoundError.__name__
    assert failed.get_indices() == [0, 2]

    succeeded = results[1]
    assert succeeded.get_infinitive() == "parler"
    assert succeeded.is_success()
    assert succeeded.get_indices() == [1]


def test_batch_handles_uppercase_inputs(bcg: BatchConjugator) -> None:
    results = bcg.conjugate(["Parler", "PARLER"])

    assert all(result.is_success() for result in results)
    assert results[0].get_conjugation() == results[1].get_conjugation()
    assert results[0].get_conjugation().get_verb_info().infinitive == "parler"


def test_batch_matches_existing_single_verb_api(bcg: BatchConjugator) -> None:
    single_verb_conjugator = CompleteConjugator(lang=Lang.fr)
    expected = single_verb_conjugator.conjugate("parler")

    result = bcg.conjugate(["parler"])[0]

    assert result.get_conjugation() == expected


def test_batch_existing_single_verb_api_still_works() -> None:
    single_verb_conjugator = CompleteConjugator(lang=Lang.fr)
    assert single_verb_conjugator.conjugate("parler")
    assert single_verb_conjugator.conjugate_mood_tense is not None


@pytest.mark.parametrize("invalid_input", [None, "parler", 123, {"parler": 1}])
def test_batch_rejects_non_list_input(
    bcg: BatchConjugator, invalid_input: object
) -> None:
    with pytest.raises(TypeError):
        bcg.conjugate(invalid_input)  # type: ignore[arg-type]


def test_batch_rejects_non_string_element(bcg: BatchConjugator) -> None:
    with pytest.raises(TypeError):
        bcg.conjugate(["parler", 42])  # type: ignore[list-item]


def test_batch_rejects_empty_string_element(bcg: BatchConjugator) -> None:
    with pytest.raises(ValueError):
        bcg.conjugate(["parler", ""])


@pytest.mark.parametrize(
    "kwargs",
    [
        {"continue_on_error": "yes"},
        {"deduplicate": 1},
        {"conjugate_pronouns": 0},
    ],
)
def test_batch_rejects_non_bool_flags(
    bcg: BatchConjugator, kwargs: dict[str, object]
) -> None:
    with pytest.raises(TypeError):
        bcg.conjugate(["parler"], **kwargs)  # type: ignore[arg-type]


def test_batch_rejects_oversized_input_before_computation(
    bcg: BatchConjugator, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls: list[str] = []
    monkeypatch.setattr(
        bcg.get_conjugator(),
        "conjugate",
        lambda infinitive, conjugate_pronouns=True: calls.append(infinitive),
    )

    oversized = [""] * (BatchConjugator.MAX_BATCH_SIZE + 1)
    with pytest.raises(ValueError, match="exceeds maximum"):
        bcg.conjugate(oversized)

    assert calls == []

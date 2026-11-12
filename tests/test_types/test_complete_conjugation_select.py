import json
from typing import Generator

import pytest
import yaml

from verbecc.core.conjugator.complete_conjugator import CompleteConjugator
from verbecc.core.defs.types.conjugation.complete_conjugation import (
    CompleteConjugation,
)
from verbecc.core.defs.types.conjugation.conjugation import Conjugation
from verbecc.core.defs.types.conjugation.mood_conjugation import MoodConjugation
from verbecc.core.defs.types.conjugation.tense_conjugation import TenseConjugation
from verbecc.core.defs.types.exceptions import InvalidMoodError
from verbecc.core.defs.types.exceptions import InvalidTenseError
from verbecc.core.defs.types.gender import Gender
from verbecc.core.defs.types.lang_code import LangCodeISO639_1 as Lang
from verbecc.core.defs.types.mood import Moods
from verbecc.core.defs.types.number import Number
from verbecc.core.defs.types.person import Person
from verbecc.core.defs.types.pronoun import Pronouns
from verbecc.core.defs.types.tense import Tenses


@pytest.fixture(scope="module")
def ccg() -> Generator[CompleteConjugator, None, None]:
    yield CompleteConjugator(lang=Lang.fr)


@pytest.fixture(scope="module")
def cc(ccg: CompleteConjugator) -> Generator[CompleteConjugation, None, None]:
    yield ccg.conjugate("parler")


@pytest.fixture(scope="module")
def ro_cc() -> Generator[CompleteConjugation, None, None]:
    yield CompleteConjugator(lang=Lang.ro).conjugate("fi")


def _leaves(complete_conjugation: CompleteConjugation) -> list[Conjugation]:
    ret: list[Conjugation] = []
    for mood in complete_conjugation:
        mood_conjugation = complete_conjugation[mood]
        for tense in mood_conjugation:
            ret.extend(mood_conjugation[tense])
    return ret


def _pronouns(tense_conjugation: TenseConjugation) -> list[object]:
    return [c.get_pronoun() for c in tense_conjugation]


# ---------------------------------------------------------------------------
# empty filter / full clone
# ---------------------------------------------------------------------------


def test_select_no_filters_returns_equal_full_clone(cc: CompleteConjugation) -> None:
    view = cc.select()

    assert view == cc
    assert view is not cc
    assert view.get_moods() is not cc.get_moods()
    assert view.get_verb_info() is not cc.get_verb_info()
    assert view.get_verb_info() == cc.get_verb_info()


def test_select_empty_lists_mean_no_restriction(cc: CompleteConjugation) -> None:
    view = cc.select(
        moods=[],
        tenses=[],
        persons=[],
        numbers=[],
        genders=[],
        pronouns=[],
    )

    assert view == cc


def test_select_verb_info_is_unchanged(cc: CompleteConjugation) -> None:
    view = cc.select(moods=[Moods.fr.Indicatif])

    assert view.get_verb_info().get_data() == cc.get_verb_info().get_data()
    assert view.get_str_id() == cc.get_str_id() == "fr:parler"


# ---------------------------------------------------------------------------
# single-condition filters
# ---------------------------------------------------------------------------


def test_select_single_mood_enum_and_string_equivalent(
    cc: CompleteConjugation,
) -> None:
    enum_view = cc.select(moods=[Moods.fr.Indicatif])
    string_view = cc.select(moods=["indicatif"])

    assert list(enum_view) == [Moods.fr.Indicatif]
    assert enum_view == string_view


def test_select_single_tense_keeps_all_moods_with_empty_placeholders(
    cc: CompleteConjugation,
) -> None:
    view = cc.select(tenses=[Tenses.fr.Présent])

    # all original moods are retained, in original order
    assert list(view) == list(cc)
    # moods that have a présent tense keep their conjugations
    assert len(view[Moods.fr.Indicatif][Tenses.fr.Présent]) == 9
    # moods without a présent tense get an empty corresponding container
    assert view[Moods.fr.Infinitif].get_data() == {Tenses.fr.Présent: []}
    assert view[Moods.fr.Participe].get_data() == {Tenses.fr.Présent: []}


def test_select_single_person(cc: CompleteConjugation) -> None:
    view = cc.select(persons=[Person.First])

    for leaf in _leaves(view):
        assert leaf.get_person() == Person.First
    # je and nous in each finite tense
    present = view[Moods.fr.Indicatif][Tenses.fr.Présent]
    assert _pronouns(present) == [Pronouns.fr.je, Pronouns.fr.nous]
    # nodes without a person (infinitive) do not match -> empty container
    assert view[Moods.fr.Infinitif][Tenses.fr.InfinitifPrésent].get_data() == []


def test_select_single_number(cc: CompleteConjugation) -> None:
    view = cc.select(numbers=[Number.Plural])

    for leaf in _leaves(view):
        assert leaf.get_number() == Number.Plural
    participe_passe = view[Moods.fr.Participe][Tenses.fr.ParticipePassé]
    assert len(participe_passe) == 2


def test_select_single_gender(cc: CompleteConjugation) -> None:
    view = cc.select(genders=[Gender.f])

    for leaf in _leaves(view):
        assert leaf.get_gender() == Gender.f
    present = view[Moods.fr.Indicatif][Tenses.fr.Présent]
    assert _pronouns(present) == [Pronouns.fr.elle, Pronouns.fr.elles]
    # imperatif has no gendered nodes -> nested empty container
    assert view[Moods.fr.Imperatif][Tenses.fr.ImperatifPrésent].get_data() == []


def test_select_single_pronoun_enum(cc: CompleteConjugation) -> None:
    view = cc.select(pronouns=[Pronouns.fr.elle])

    for leaf in _leaves(view):
        assert leaf.get_pronoun() == Pronouns.fr.elle
    assert len(view[Moods.fr.Indicatif][Tenses.fr.Présent]) == 1


# ---------------------------------------------------------------------------
# combined conditions
# ---------------------------------------------------------------------------


def test_select_combined_mood_tense_person_gender(cc: CompleteConjugation) -> None:
    view = cc.select(
        moods=[Moods.fr.Indicatif, Moods.fr.Subjonctif],
        tenses=[Tenses.fr.Présent],
        persons=[Person.Third],
        genders=[Gender.f],
    )

    for mood in (Moods.fr.Indicatif, Moods.fr.Subjonctif):
        tense_conjugation = view[mood][Tenses.fr.Présent]
        assert _pronouns(tense_conjugation) == [
            Pronouns.fr.elle,
            Pronouns.fr.elles,
        ]
        for leaf in tense_conjugation:
            assert leaf.get_person() == Person.Third
            assert leaf.get_gender() == Gender.f


def test_select_combined_string_names_and_enums(cc: CompleteConjugation) -> None:
    view = cc.select(
        moods=["indicatif", Moods.fr.Subjonctif],
        tenses=["présent"],
        persons=["1"],
        numbers=["s"],
        pronouns=["je"],
    )

    expected = cc.select(
        moods=[Moods.fr.Indicatif, Moods.fr.Subjonctif],
        tenses=[Tenses.fr.Présent],
        persons=[Person.First],
        numbers=[Number.Singular],
        pronouns=[Pronouns.fr.je],
    )
    assert view == expected
    for mood in (Moods.fr.Indicatif, Moods.fr.Subjonctif):
        assert _pronouns(view[mood][Tenses.fr.Présent]) == [Pronouns.fr.je]


# ---------------------------------------------------------------------------
# third-person gender
# ---------------------------------------------------------------------------


def test_select_third_person_gender_feminine(cc: CompleteConjugation) -> None:
    view = cc.select(persons=[Person.Third], genders=[Gender.f])

    present = view[Moods.fr.Indicatif][Tenses.fr.Présent]
    assert _pronouns(present) == [Pronouns.fr.elle, Pronouns.fr.elles]
    # "on" is third person but has no gender -> excluded
    assert Pronouns.fr.on not in _pronouns(present)


def test_select_third_person_gender_masculine(cc: CompleteConjugation) -> None:
    view = cc.select(persons=[Person.Third], genders=[Gender.m])

    present = view[Moods.fr.Indicatif][Tenses.fr.Présent]
    assert _pronouns(present) == [Pronouns.fr.il, Pronouns.fr.ils]


def test_select_gender_does_not_match_personless_participle(
    cc: CompleteConjugation,
) -> None:
    view = cc.select(persons=[Person.Third], genders=[Gender.f])

    # participe-passé has gender but no person, so the person filter excludes it
    assert view[Moods.fr.Participe][Tenses.fr.ParticipePassé].get_data() == []


# ---------------------------------------------------------------------------
# pronouns by current-language name
# ---------------------------------------------------------------------------


def test_select_pronouns_string_names(cc: CompleteConjugation) -> None:
    view = cc.select(pronouns=["je", "nous"])

    present = view[Moods.fr.Indicatif][Tenses.fr.Présent]
    assert _pronouns(present) == [Pronouns.fr.je, Pronouns.fr.nous]
    # tenses without pronouns keep empty containers rather than disappearing
    assert view[Moods.fr.Participe][Tenses.fr.ParticipePassé].get_data() == []
    # imperatif has "nous" but no "je"
    imperatif = view[Moods.fr.Imperatif][Tenses.fr.ImperatifPrésent]
    assert _pronouns(imperatif) == [Pronouns.fr.nous]


# ---------------------------------------------------------------------------
# no hits / nested empty containers
# ---------------------------------------------------------------------------


def test_select_no_hits_returns_empty_containers_without_error(
    cc: CompleteConjugation,
) -> None:
    view = cc.select(
        moods=[Moods.fr.Participe],
        pronouns=[Pronouns.fr.il],
    )

    mood_conjugation = view[Moods.fr.Participe]
    assert isinstance(mood_conjugation, MoodConjugation)
    assert mood_conjugation.get_data() == {
        Tenses.fr.ParticipePresent: [],
        Tenses.fr.ParticipePassé: [],
    }


def test_select_valid_tense_absent_from_mood_is_empty_container(
    cc: CompleteConjugation,
) -> None:
    view = cc.select(
        moods=[Moods.fr.Indicatif],
        tenses=[Tenses.fr.ImperatifPrésent],
    )

    assert view[Moods.fr.Indicatif].get_data() == {
        Tenses.fr.ImperatifPrésent: []
    }


def test_select_valid_mood_absent_from_conjugation_is_empty_container(
    ro_cc: CompleteConjugation,
) -> None:
    # Romanian defines Condițional in the Mood enum but no verb uses it
    view = ro_cc.select(moods=[Moods.ro.Condițional])

    assert list(view) == [Moods.ro.Condițional]
    assert view[Moods.ro.Condițional].get_data() == {}


def test_select_absent_mood_appended_after_original_order(
    ro_cc: CompleteConjugation,
) -> None:
    view = ro_cc.select(
        moods=[Moods.ro.Condițional, Moods.ro.Indicativ],
    )

    # original mood keeps its position; the absent requested mood is appended
    assert list(view) == [Moods.ro.Indicativ, Moods.ro.Condițional]


def test_select_deduplicates_filter_values(cc: CompleteConjugation) -> None:
    view = cc.select(
        moods=[Moods.fr.Indicatif, "indicatif", Moods.fr.Indicatif],
    )

    assert list(view) == [Moods.fr.Indicatif]


# ---------------------------------------------------------------------------
# ordering
# ---------------------------------------------------------------------------


def test_select_preserves_original_mood_and_tense_order(
    cc: CompleteConjugation,
) -> None:
    view = cc.select(
        moods=[Moods.fr.Subjonctif, Moods.fr.Indicatif],
        tenses=[Tenses.fr.Imparfait, Tenses.fr.Présent],
    )

    # filter list order is ignored in favor of the source order
    assert list(view) == [Moods.fr.Indicatif, Moods.fr.Subjonctif]
    assert list(view[Moods.fr.Indicatif]) == [
        Tenses.fr.Présent,
        Tenses.fr.Imparfait,
    ]
    assert list(view[Moods.fr.Subjonctif]) == [
        Tenses.fr.Présent,
        Tenses.fr.Imparfait,
    ]


def test_select_preserves_conjugation_order(cc: CompleteConjugation) -> None:
    view = cc.select(
        moods=[Moods.fr.Indicatif],
        tenses=[Tenses.fr.Présent],
        persons=[Person.Third],
    )

    original_pronouns = _pronouns(cc[Moods.fr.Indicatif][Tenses.fr.Présent])
    view_pronouns = _pronouns(view[Moods.fr.Indicatif][Tenses.fr.Présent])
    assert view_pronouns == [
        p for p in original_pronouns if p in set(view_pronouns)
    ]


# ---------------------------------------------------------------------------
# illegal conditions
# ---------------------------------------------------------------------------


def test_select_unknown_mood_string_raises_invalid_mood_error(
    cc: CompleteConjugation,
) -> None:
    with pytest.raises(InvalidMoodError):
        cc.select(moods=["oops"])


def test_select_unknown_tense_string_raises_invalid_tense_error(
    cc: CompleteConjugation,
) -> None:
    with pytest.raises(InvalidTenseError):
        cc.select(tenses=["oops"])


def test_select_foreign_language_mood_raises_invalid_mood_error(
    cc: CompleteConjugation,
) -> None:
    with pytest.raises(InvalidMoodError):
        cc.select(moods=[Moods.es.Indicativo])


def test_select_illegal_person_number_gender_pronoun_raise_value_error(
    cc: CompleteConjugation,
) -> None:
    with pytest.raises(ValueError):
        cc.select(persons=["9"])
    with pytest.raises(ValueError):
        cc.select(numbers=["x"])
    with pytest.raises(ValueError):
        cc.select(genders=["x"])
    with pytest.raises(ValueError):
        cc.select(pronouns=["bogus-pronoun"])


# ---------------------------------------------------------------------------
# parent-child links
# ---------------------------------------------------------------------------


def test_select_clone_parent_chain_and_str_id(cc: CompleteConjugation) -> None:
    view = cc.select(
        moods=[Moods.fr.Indicatif],
        tenses=[Tenses.fr.Présent],
        pronouns=[Pronouns.fr.elle],
    )

    leaf = view[Moods.fr.Indicatif][Tenses.fr.Présent][0]
    tense_conjugation = leaf.get_parent()
    mood_conjugation = tense_conjugation.get_parent()
    moods_conjugation = mood_conjugation.get_parent()
    root = moods_conjugation.get_parent()

    assert isinstance(tense_conjugation, TenseConjugation)
    assert isinstance(mood_conjugation, MoodConjugation)
    assert root is view
    assert leaf.get_str_id() == "fr:parler:indicatif:présent:3:s:f:elle"
    assert view.get_verb_info().get_parent() is view


# ---------------------------------------------------------------------------
# serialization
# ---------------------------------------------------------------------------


def test_select_to_json_matches_expected_primitive_data(
    cc: CompleteConjugation,
) -> None:
    view = cc.select(
        moods=[Moods.fr.Indicatif],
        tenses=[Tenses.fr.Présent],
        pronouns=[Pronouns.fr.elle],
    )

    assert json.loads(view.to_json()) == {
        "verb": cc.get_verb_info().get_data(),
        "moods": {
            "indicatif": {
                "présent": [
                    {
                        "c": ["elle parle"],
                        "g": "f",
                        "n": "s",
                        "p": "3",
                        "pr": "elle",
                    }
                ]
            }
        },
    }


def test_select_to_yaml_matches_json_with_integer_person(
    cc: CompleteConjugation,
) -> None:
    view = cc.select(
        moods=[Moods.fr.Indicatif],
        tenses=[Tenses.fr.Présent],
        pronouns=[Pronouns.fr.elle],
    )

    yaml_data = yaml.safe_load(view.to_yaml())
    assert yaml_data["moods"]["indicatif"]["présent"] == [
        {"c": ["elle parle"], "g": "f", "n": "s", "p": 3, "pr": "elle"}
    ]
    assert yaml_data["verb"] == json.loads(cc.get_verb_info().to_json())


def test_select_empty_containers_serialize(cc: CompleteConjugation) -> None:
    view = cc.select(
        moods=[Moods.fr.Participe],
        pronouns=[Pronouns.fr.il],
    )

    json_data = json.loads(view.to_json())
    assert json_data["moods"]["participe"] == {
        "participe-présent": [],
        "participe-passé": [],
    }
    assert yaml.safe_load(view.to_yaml())["moods"]["participe"] == {
        "participe-présent": [],
        "participe-passé": [],
    }


def test_select_empty_mood_container_serializes(ro_cc: CompleteConjugation) -> None:
    view = ro_cc.select(moods=[Moods.ro.Condițional])

    assert json.loads(view.to_json())["moods"] == {"condițional": {}}
    assert yaml.safe_load(view.to_yaml())["moods"] == {"condițional": {}}


# ---------------------------------------------------------------------------
# original object isolation
# ---------------------------------------------------------------------------


def test_select_view_mutation_does_not_affect_original(
    cc: CompleteConjugation,
) -> None:
    original_json = cc.to_json()
    view = cc.select(
        moods=[Moods.fr.Indicatif],
        tenses=[Tenses.fr.Présent],
    )

    leaf = view[Moods.fr.Indicatif][Tenses.fr.Présent][0]
    leaf.append("HACKED")
    view[Moods.fr.Indicatif][Tenses.fr.Présent].append(leaf)
    view[Moods.fr.Indicatif][Tenses.fr.Présent][0].set_number(Number.Plural)

    assert cc.to_json() == original_json
    original_present = cc[Moods.fr.Indicatif][Tenses.fr.Présent]
    assert len(original_present) == 9
    assert all("HACKED" not in c.get_conjugations() for c in original_present)
    # the original first-singular "je" node keeps its original number
    original_je = original_present[0]
    assert original_je.get_pronoun() == Pronouns.fr.je
    assert original_je.get_number() == Number.Singular
    # the mutated view no longer equals the original
    assert view != cc


def test_select_tree_nodes_are_distinct_objects(cc: CompleteConjugation) -> None:
    view = cc.select(moods=[Moods.fr.Indicatif], tenses=[Tenses.fr.Présent])

    assert view[Moods.fr.Indicatif] is not cc[Moods.fr.Indicatif]
    assert (
        view[Moods.fr.Indicatif][Tenses.fr.Présent]
        is not cc[Moods.fr.Indicatif][Tenses.fr.Présent]
    )
    original_leaves = cc[Moods.fr.Indicatif][Tenses.fr.Présent]
    view_leaves = view[Moods.fr.Indicatif][Tenses.fr.Présent]
    for original_leaf, view_leaf in zip(original_leaves, view_leaves):
        assert original_leaf is not view_leaf
        assert (
            original_leaf.get_conjugations()
            is not view_leaf.get_conjugations()
        )


def test_select_original_mutation_does_not_affect_existing_view(
    ccg: CompleteConjugator,
) -> None:
    original = ccg.conjugate("parler")
    view = original.select(
        moods=[Moods.fr.Indicatif],
        tenses=[Tenses.fr.Présent],
        pronouns=[Pronouns.fr.je],
    )
    view_json = view.to_json()

    original[Moods.fr.Indicatif][Tenses.fr.Présent][0].append("MUTATED")

    assert view.to_json() == view_json

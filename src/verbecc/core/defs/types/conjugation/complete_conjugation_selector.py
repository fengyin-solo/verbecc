import sys
from typing import Optional

if sys.version_info >= (3, 11):
    from enum import StrEnum
else:
    from backports.strenum import StrEnum

from verbecc.core.defs.types.conjugation.complete_conjugation import (
    CompleteConjugation,
)
from verbecc.core.defs.types.conjugation.conjugation import Conjugation
from verbecc.core.defs.types.conjugation.mood_conjugation import MoodConjugation
from verbecc.core.defs.types.conjugation.moods_conjugation import MoodsConjugation
from verbecc.core.defs.types.conjugation.tense_conjugation import TenseConjugation
from verbecc.core.defs.types.conjugation.verb_info import VerbInfo
from verbecc.core.defs.types.exceptions import InvalidMoodError
from verbecc.core.defs.types.exceptions import InvalidTenseError
from verbecc.core.defs.types.gender import Gender
from verbecc.core.defs.types.lang_code import LangCodeISO639_1
from verbecc.core.defs.types.mood import Mood
from verbecc.core.defs.types.mood import MoodFactory
from verbecc.core.defs.types.number import Number
from verbecc.core.defs.types.person import Person
from verbecc.core.defs.types.pronoun import Pronoun
from verbecc.core.defs.types.pronoun import PronounFactory
from verbecc.core.defs.types.tense import Tense
from verbecc.core.defs.types.tense import TenseFactory


class CompleteConjugationSelector:
    """
    Builds filtered, deep-cloned CompleteConjugation "select" views.

    Each of the six optional filter groups accepts the language enums or their
    current-language string names. An empty (None) filter group means "no
    restriction". Nodes are walked in original mood and tense order so the
    view ordering always follows the source CompleteConjugation, never the
    order in which filter values were supplied. Combinations that have no
    matching nodes are retained as empty containers instead of raising; only
    unknown mood or tense names are rejected, using the existing
    InvalidMoodError / InvalidTenseError semantics.
    """

    @classmethod
    def select(
        cls,
        complete_conjugation: CompleteConjugation,
        moods: Optional[list[Mood | str]] = None,
        tenses: Optional[list[Tense | str]] = None,
        persons: Optional[list[Person | str]] = None,
        numbers: Optional[list[Number | str]] = None,
        genders: Optional[list[Gender | str]] = None,
        pronouns: Optional[list[Pronoun | str]] = None,
    ) -> CompleteConjugation:
        lang = complete_conjugation.get_verb_info().lang
        mood_filter = cls._resolve_moods(lang, moods)
        tense_filter = cls._resolve_tenses(lang, tenses)
        person_filter = cls._resolve_enum(persons, Person)
        number_filter = cls._resolve_enum(numbers, Number)
        gender_filter = cls._resolve_enum(genders, Gender)
        pronoun_filter = cls._resolve_pronouns(lang, pronouns)
        moods_conjugation = cls._select_moods(
            complete_conjugation.get_moods(),
            mood_filter,
            tense_filter,
            person_filter,
            number_filter,
            gender_filter,
            pronoun_filter,
        )
        return CompleteConjugation(
            cls._clone_verb_info(complete_conjugation.get_verb_info()),
            moods_conjugation,
        )

    @classmethod
    def _resolve_moods(
        cls,
        lang: LangCodeISO639_1,
        values: Optional[list[Mood | str]],
    ) -> Optional[list[Mood]]:
        if not values:
            return None
        ret: list[Mood] = []
        for value in cls._dedupe(values):
            try:
                ret.append(MoodFactory.from_string(lang, str(value)))
            except ValueError as err:
                raise InvalidMoodError() from err
        return ret

    @classmethod
    def _resolve_tenses(
        cls,
        lang: LangCodeISO639_1,
        values: Optional[list[Tense | str]],
    ) -> Optional[list[Tense]]:
        if not values:
            return None
        ret: list[Tense] = []
        for value in cls._dedupe(values):
            try:
                ret.append(TenseFactory.from_string(lang, str(value)))
            except ValueError as err:
                raise InvalidTenseError() from err
        return ret

    @classmethod
    def _resolve_pronouns(
        cls,
        lang: LangCodeISO639_1,
        values: Optional[list[Pronoun | str]],
    ) -> Optional[list[Pronoun]]:
        if not values:
            return None
        ret: list[Pronoun] = []
        for value in cls._dedupe(values):
            ret.append(PronounFactory.from_string(lang, str(value)))
        return ret

    @classmethod
    def _resolve_enum(
        cls,
        values: Optional[list[StrEnum | str]],
        enum_type: type[StrEnum],
    ) -> Optional[list[StrEnum]]:
        if not values:
            return None
        return [enum_type(str(value)) for value in cls._dedupe(values)]

    @classmethod
    def _dedupe(cls, values: list[StrEnum | str]) -> list[StrEnum | str]:
        seen: set[str] = set()
        ret: list[StrEnum | str] = []
        for value in values:
            key = str(value)
            if key not in seen:
                seen.add(key)
                ret.append(value)
        return ret

    @classmethod
    def _select_moods(
        cls,
        original: MoodsConjugation,
        mood_filter: Optional[list[Mood]],
        tense_filter: Optional[list[Tense]],
        person_filter: Optional[list[Person]],
        number_filter: Optional[list[Number]],
        gender_filter: Optional[list[Gender]],
        pronoun_filter: Optional[list[Pronoun]],
    ) -> MoodsConjugation:
        ret = MoodsConjugation()
        retained: set[Mood] = set()
        for mood in original:
            if mood_filter is None or mood in mood_filter:
                ret[mood] = cls._select_mood(
                    original[mood],
                    tense_filter,
                    person_filter,
                    number_filter,
                    gender_filter,
                    pronoun_filter,
                )
                retained.add(mood)
        if mood_filter is not None:
            for mood in mood_filter:
                if mood not in retained:
                    ret[mood] = MoodConjugation(mood)
        return ret

    @classmethod
    def _select_mood(
        cls,
        original: MoodConjugation,
        tense_filter: Optional[list[Tense]],
        person_filter: Optional[list[Person]],
        number_filter: Optional[list[Number]],
        gender_filter: Optional[list[Gender]],
        pronoun_filter: Optional[list[Pronoun]],
    ) -> MoodConjugation:
        ret = MoodConjugation(original.get_mood())
        retained: set[Tense] = set()
        for tense in original:
            if tense_filter is None or tense in tense_filter:
                ret[tense] = cls._select_tense(
                    original[tense],
                    tense,
                    person_filter,
                    number_filter,
                    gender_filter,
                    pronoun_filter,
                )
                retained.add(tense)
        if tense_filter is not None:
            for tense in tense_filter:
                if tense not in retained:
                    ret[tense] = TenseConjugation(tense)
        return ret

    @classmethod
    def _select_tense(
        cls,
        original: TenseConjugation,
        tense: Tense,
        person_filter: Optional[list[Person]],
        number_filter: Optional[list[Number]],
        gender_filter: Optional[list[Gender]],
        pronoun_filter: Optional[list[Pronoun]],
    ) -> TenseConjugation:
        ret = TenseConjugation(tense)
        for conjugation in original:
            if cls._conjugation_matches(
                conjugation,
                person_filter,
                number_filter,
                gender_filter,
                pronoun_filter,
            ):
                ret.append(cls._clone_conjugation(conjugation))
        return ret

    @classmethod
    def _conjugation_matches(
        cls,
        conjugation: Conjugation,
        person_filter: Optional[list[Person]],
        number_filter: Optional[list[Number]],
        gender_filter: Optional[list[Gender]],
        pronoun_filter: Optional[list[Pronoun]],
    ) -> bool:
        return (
            cls._field_matches(conjugation.get_person(), person_filter)
            and cls._field_matches(conjugation.get_number(), number_filter)
            and cls._field_matches(conjugation.get_gender(), gender_filter)
            and cls._field_matches(conjugation.get_pronoun(), pronoun_filter)
        )

    @classmethod
    def _field_matches(
        cls,
        value: Optional[StrEnum],
        filter_values: Optional[list[StrEnum]],
    ) -> bool:
        if filter_values is None:
            return True
        return value is not None and value in filter_values

    @classmethod
    def _clone_conjugation(cls, original: Conjugation) -> Conjugation:
        return Conjugation(
            original.get_person(),
            original.get_number(),
            original.get_gender(),
            original.get_pronoun(),
            list(original.get_conjugations()),
        )

    @classmethod
    def _clone_verb_info(cls, original: VerbInfo) -> VerbInfo:
        return VerbInfo(
            original.lang,
            original.infinitive,
            original.predicted,
            original.pred_score,
            original.template,
            original.translation_en,
            original.stem,
        )

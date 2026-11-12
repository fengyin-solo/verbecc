from typing import Iterable, Optional

from verbecc.core.defs.types.conjugation.abstract_conjugation import AbstractConjugation
from verbecc.core.defs.types.conjugation.verb_info import VerbInfo
from verbecc.core.defs.types.gender import Gender
from verbecc.core.defs.types.mood import Mood
from verbecc.core.defs.types.number import Number
from verbecc.core.defs.types.person import Person
from verbecc.core.defs.types.pronoun import Pronoun
from verbecc.core.defs.types.tense import Tense
from verbecc.core.defs.types.conjugation.mood_conjugation import MoodConjugation
from verbecc.core.defs.types.conjugation.moods_conjugation import MoodsConjugation
from verbecc.core.defs.types.conjugation.complete_conjugation_data import (
    CompleteConjugationData,
)
from verbecc.core.utils.config.verbecc_config_util import VerbeccConfigUtil

config = VerbeccConfigUtil().load_config()


class CompleteConjugation(AbstractConjugation):

    def __init__(
        self,
        verb_info: VerbInfo,
        moods_conjugation: MoodsConjugation,
    ) -> None:
        super().__init__()
        verb_info.set_parent(self)
        self._verb_info = verb_info
        moods_conjugation.set_parent(self)
        self._moods_conjugation = moods_conjugation

    def __eq__(self, other: object) -> bool:
        if other is None:
            return False
        elif not isinstance(other, CompleteConjugation):
            raise TypeError()
        return (
            self._verb_info == other._verb_info
            and self._moods_conjugation == other._moods_conjugation
        )

    def __ne__(self, other: object) -> bool:
        return not self.__eq__(other)

    def __hash__(self) -> int:
        return hash((self._verb_info, self._moods_conjugation))

    def __getitem__(self, key: Mood) -> MoodConjugation:
        return self._moods_conjugation[key]

    def __setitem__(self, key: Mood, value: MoodConjugation) -> None:
        self._moods_conjugation[key] = value

    def __len__(self) -> int:
        return len(self._moods_conjugation)

    def __iter__(self) -> Iterable[Mood]:
        return iter(self._moods_conjugation.get_data().keys())

    def __contains__(self, key: Mood) -> bool:
        return key in self._moods_conjugation

    def get_verb_info(self) -> VerbInfo:
        return self._verb_info

    def get_moods(self) -> MoodsConjugation:
        return self._moods_conjugation

    def select(
        self,
        moods: Optional[list[Mood | str]] = None,
        tenses: Optional[list[Tense | str]] = None,
        persons: Optional[list[Person | str]] = None,
        numbers: Optional[list[Number | str]] = None,
        genders: Optional[list[Gender | str]] = None,
        pronouns: Optional[list[Pronoun | str]] = None,
    ) -> "CompleteConjugation":
        """
        Returns a deep-cloned CompleteConjugation view containing only the
        nodes matching the supplied filter groups.

        Each filter group is optional: None (the default) or an empty list
        means "no restriction" for that group. Values may be the language
        enums or their current-language string names. Original mood and tense
        order is preserved (filter list order is never used for sorting).
        Combinations with no matching nodes are kept as empty containers;
        unknown mood or tense names raise InvalidMoodError / InvalidTenseError.
        The returned view is fully independent: mutating it never affects this
        object.
        """
        from verbecc.core.defs.types.conjugation.complete_conjugation_selector import (
            CompleteConjugationSelector,
        )

        return CompleteConjugationSelector.select(
            self,
            moods=moods,
            tenses=tenses,
            persons=persons,
            numbers=numbers,
            genders=genders,
            pronouns=pronouns,
        )

    def get_data(self) -> CompleteConjugationData:
        return {
            "verb": self._verb_info.get_data(),
            "moods": self._moods_conjugation.get_data(),
        }

    def get_str_id(self) -> str:
        """
        Return unique string identifier consisting of
        lang:verb
        E.g. "fr:parler"
        E.g. "fr:parler"
        """
        # This is the root node, so it has no parent.
        return self._verb_info.get_str_id()

from typing import Optional

from verbecc.core.defs.types.conjugation.complete_conjugation import (
    CompleteConjugation,
)


class BatchConjugationResult:
    """
    Outcome of conjugating one (possibly deduplicated) batch input verb.

    A result always retains the index of its first occurrence in the input
    list and the original spelling of that first occurrence. When
    deduplication is enabled, ``indices`` additionally holds every original
    input position that maps to this unique result.

    A successful result carries a ``CompleteConjugation`` with its error
    attributes left ``None``. A failed result carries the discriminable
    exception type name and the exception message instead, so a single bad
    verb never corrupts the structure of the whole batch.
    """

    def __init__(
        self,
        index: int,
        infinitive: str,
        indices: Optional[list[int]] = None,
        conjugation: Optional[CompleteConjugation] = None,
        error_type: Optional[str] = None,
        error_message: Optional[str] = None,
    ) -> None:
        self._index = index
        self._infinitive = infinitive
        self._indices = list(indices) if indices is not None else [index]
        self._conjugation = conjugation
        self._error_type = error_type
        self._error_message = error_message

    def get_index(self) -> int:
        """Index of the first occurrence of this verb in the input list."""
        return self._index

    def get_indices(self) -> list[int]:
        """
        Every original input index represented by this result.
        Without deduplication this is a single-element list; with
        deduplication it also contains the positions of all duplicates.
        """
        return list(self._indices)

    def get_infinitive(self) -> str:
        """Original spelling of the verb at its first occurrence."""
        return self._infinitive

    def get_conjugation(self) -> Optional[CompleteConjugation]:
        """The complete conjugation, or ``None`` when this result failed."""
        return self._conjugation

    def get_error_type(self) -> Optional[str]:
        """Discriminable exception class name, or ``None`` on success."""
        return self._error_type

    def get_error_message(self) -> Optional[str]:
        """Exception message, or ``None`` on success."""
        return self._error_message

    def is_success(self) -> bool:
        return self._conjugation is not None

    def is_error(self) -> bool:
        return self._conjugation is None

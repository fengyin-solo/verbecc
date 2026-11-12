from typing import Optional

from verbecc.core.conjugator.batch_conjugation_result import (
    BatchConjugationResult,
)
from verbecc.core.conjugator.complete_conjugator import CompleteConjugator
from verbecc.core.defs.types.conjugation.complete_conjugation import (
    CompleteConjugation,
)
from verbecc.core.defs.types.lang_code import LangCodeISO639_1
from verbecc.core.defs.types.lang_specific_options import LangSpecificOptions
from verbecc.core.utils.logging_utils import LoggingUtils


class BatchConjugator:
    """
    Conjugates an ordered batch of infinitive verbs using a single shared
    ``CompleteConjugator``, i.e. one loaded language/inflector instance is
    reused for every verb in the batch.

    Each input position maps to exactly one ``BatchConjugationResult`` which
    retains its input index (and, when deduplicating, all duplicate indices),
    the original spelling, and either a ``CompleteConjugation`` or a
    discriminable error.

    By default conjugation stops at the first error and the original
    exception is re-raised. With ``continue_on_error=True`` the remaining
    verbs are still processed and each failure is recorded in place.

    With ``deduplicate=True`` only the first-occurrence result for each
    normalized (lowercased) input is computed and returned, in first
    occurrence order; every duplicate position still maps to that unique
    result through ``BatchConjugationResult.get_indices()``.
    """

    MAX_BATCH_SIZE: int = 1000

    def __init__(
        self,
        lang: LangCodeISO639_1,
        lang_specific_options: Optional[LangSpecificOptions] = None,
    ) -> None:
        self._conjugator = CompleteConjugator(lang, lang_specific_options)
        self._logger = LoggingUtils.get_logger(self.__class__.__name__)

    def conjugate(
        self,
        infinitives: list[str],
        continue_on_error: bool = False,
        deduplicate: bool = False,
        conjugate_pronouns: bool = True,
    ) -> list[BatchConjugationResult]:
        """
        Conjugate an ordered list of infinitive verbs.

        :param infinitives: ordered verb infinitives to conjugate
        :param continue_on_error: if False (default) the first error stops
            the batch and the original exception is re-raised; if True the
            rest of the batch is processed and errors are recorded in place
        :param deduplicate: if True only the first occurrence of each
            lowercased input is conjugated, without changing first
            occurrence order
        :param conjugate_pronouns: forwarded to ``CompleteConjugator``
        """
        self._validate(
            infinitives, continue_on_error, deduplicate, conjugate_pronouns
        )
        if len(infinitives) == 0:
            return []

        results: list[BatchConjugationResult] = []
        for infinitive, indices in self._plan_work_items(infinitives, deduplicate):
            try:
                conjugation: CompleteConjugation = self._conjugator.conjugate(
                    infinitive, conjugate_pronouns=conjugate_pronouns
                )
            except Exception as exception:
                if not continue_on_error:
                    raise
                self._logger.warning(
                    "Failed to conjugate '%s': %s",
                    infinitive,
                    exception,
                    exc_info=True,
                )
                results.append(
                    self._build_error_result(indices[0], infinitive, indices, exception)
                )
            else:
                results.append(
                    BatchConjugationResult(
                        indices[0],
                        infinitive,
                        indices=indices,
                        conjugation=conjugation,
                    )
                )
        return results

    def get_conjugator(self) -> CompleteConjugator:
        """The shared single-verb conjugator reused for every batch item."""
        return self._conjugator

    def _plan_work_items(
        self, infinitives: list[str], deduplicate: bool
    ) -> list[tuple[str, list[int]]]:
        """
        Build the ordered list of work items as
        (first-occurrence spelling, original input indices) tuples.
        """
        if not deduplicate:
            return [(infinitive, [index]) for index, infinitive in enumerate(infinitives)]
        indices_by_normalized: dict[str, list[int]] = {}
        order: list[str] = []
        for index, infinitive in enumerate(infinitives):
            normalized = infinitive.lower()
            if normalized not in indices_by_normalized:
                indices_by_normalized[normalized] = []
                order.append(normalized)
            indices_by_normalized[normalized].append(index)
        return [
            (infinitives[indices_by_normalized[normalized][0]], indices_by_normalized[normalized])
            for normalized in order
        ]

    def _build_error_result(
        self,
        index: int,
        infinitive: str,
        indices: list[int],
        exception: Exception,
    ) -> BatchConjugationResult:
        error_type = type(exception).__name__
        error_message = str(exception)
        if not error_message:
            error_message = "{} while conjugating '{}'".format(
                error_type, infinitive
            )
        return BatchConjugationResult(
            index,
            infinitive,
            indices=indices,
            error_type=error_type,
            error_message=error_message,
        )

    def _validate(
        self,
        infinitives: list[str],
        continue_on_error: bool,
        deduplicate: bool,
        conjugate_pronouns: bool,
    ) -> None:
        """Validate all arguments before any conjugation is attempted."""
        if not isinstance(infinitives, list):
            raise TypeError("infinitives must be a list of strings")
        if not isinstance(continue_on_error, bool):
            raise TypeError("continue_on_error must be a bool")
        if not isinstance(deduplicate, bool):
            raise TypeError("deduplicate must be a bool")
        if not isinstance(conjugate_pronouns, bool):
            raise TypeError("conjugate_pronouns must be a bool")
        if len(infinitives) > self.MAX_BATCH_SIZE:
            raise ValueError(
                "batch size {} exceeds maximum of {}".format(
                    len(infinitives), self.MAX_BATCH_SIZE
                )
            )
        for index, infinitive in enumerate(infinitives):
            if not isinstance(infinitive, str):
                raise TypeError(
                    "infinitives[{}] must be a string, got {}".format(
                        index, type(infinitive).__name__
                    )
                )
            if not infinitive:
                raise ValueError(
                    "infinitives[{}] must be a non-empty string".format(index)
                )

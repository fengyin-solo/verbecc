import sys

if sys.version_info >= (3, 11):
    from enum import StrEnum
else:
    from backports.strenum import StrEnum


class VerbMatchReason(StrEnum):
    """
    Why a verb was returned by VerbCatalog.search.

    Members are declared in match-priority order: an exact infinitive match
    outranks an accent-insensitive exact match, which outranks a prefix match,
    then a substring match, and finally an English translation match.
    """

    exact = "exact"
    exact_no_accents = "exact_no_accents"
    prefix = "prefix"
    substring = "substring"
    translation_en = "translation_en"

from verbecc.core.defs.types.data.verb import Verb
from verbecc.core.defs.types.data.verb_catalog_entry import VerbCatalogEntry
from verbecc.core.defs.types.data.verb_match_reason import VerbMatchReason
from verbecc.core.defs.types.data.verbs import Verbs
from verbecc.core.defs.types.lang_code import LangCodeISO639_1
from verbecc.core.parsers.verbs_parser import VerbsParser
from verbecc.core.utils.string_utils import strip_accents


class VerbCatalog:
    """
    Read-only, in-memory search catalog for one language's verbs.

    The catalog is built exactly once at construction time from the parsed
    ``Verbs`` and ``Verb`` metadata of the given language. ``search`` only
    reads that immutable index: it never re-parses the XML data, never
    mutates the parser output, and never invokes machine-learning template
    prediction, so unknown queries simply return no results.
    """

    DEFAULT_SEARCH_LIMIT: int = 25
    MAX_SEARCH_LIMIT: int = 100

    _REASON_PRIORITY: tuple[VerbMatchReason, ...] = (
        VerbMatchReason.exact,
        VerbMatchReason.exact_no_accents,
        VerbMatchReason.prefix,
        VerbMatchReason.substring,
        VerbMatchReason.translation_en,
    )

    def __init__(self, lang: LangCodeISO639_1) -> None:
        self.lang = lang
        verbs: Verbs = VerbsParser(lang).parse()
        self._index: tuple[tuple[Verb, str], ...] = tuple(
            (verb, verb.translation_en.lower()) for verb in verbs
        )

    def __len__(self) -> int:
        """
        Returns the number of verbs indexed by the catalog.
        """
        return len(self._index)

    def search(
        self, query: str, limit: int = DEFAULT_SEARCH_LIMIT
    ) -> list[VerbCatalogEntry]:
        """
        Searches the catalog for verbs matching ``query``.

        Matching is case-insensitive and uses five tiers, in priority order:
        exact infinitive, accent-insensitive exact infinitive, prefix on the
        accent-insensitive infinitive, substring on the accent-insensitive
        infinitive, and substring on the English translation. Results are
        ordered by tier and then by infinitive; each verb appears at most
        once, with all of its matching reasons merged together.

        :param query: text to search for; an empty or whitespace-only query
            returns an empty list.
        :param limit: maximum number of results to return; must be a positive
            integer no greater than ``MAX_SEARCH_LIMIT``.
        """
        self._validate_limit(limit)
        if not isinstance(query, str) or query.strip() == "":
            return []
        query_lower = query.lower()
        query_no_accents = strip_accents(query_lower)
        ranked_matches: list[tuple[int, VerbCatalogEntry]] = []
        for verb, translation_lower in self._index:
            reasons = self._match_verb(
                verb, translation_lower, query_lower, query_no_accents
            )
            if not reasons:
                continue
            entry = VerbCatalogEntry(
                verb.infinitive, verb.translation_en, verb.template, reasons
            )
            ranked_matches.append((self._rank(reasons), entry))
        ranked_matches.sort(key=lambda match: (match[0], match[1].infinitive))
        return [entry for _, entry in ranked_matches[:limit]]

    def _match_verb(
        self,
        verb: Verb,
        translation_lower: str,
        query_lower: str,
        query_no_accents: str,
    ) -> list[VerbMatchReason]:
        reasons: list[VerbMatchReason] = []
        form_reason = self._match_form(verb, query_lower, query_no_accents)
        if form_reason is not None:
            reasons.append(form_reason)
        if query_lower in translation_lower:
            reasons.append(VerbMatchReason.translation_en)
        return reasons

    def _match_form(
        self, verb: Verb, query_lower: str, query_no_accents: str
    ) -> VerbMatchReason | None:
        if verb.infinitive == query_lower:
            return VerbMatchReason.exact
        if verb.infinitive_no_accents == query_no_accents:
            return VerbMatchReason.exact_no_accents
        if verb.infinitive_no_accents.startswith(query_no_accents):
            return VerbMatchReason.prefix
        if query_no_accents in verb.infinitive_no_accents:
            return VerbMatchReason.substring
        return None

    def _rank(self, reasons: list[VerbMatchReason]) -> int:
        return min(self._REASON_PRIORITY.index(reason) for reason in reasons)

    def _validate_limit(self, limit: int) -> None:
        if (
            isinstance(limit, bool)
            or not isinstance(limit, int)
            or limit <= 0
            or limit > self.MAX_SEARCH_LIMIT
        ):
            raise ValueError(
                "limit must be a positive integer no greater than {}".format(
                    self.MAX_SEARCH_LIMIT
                )
            )

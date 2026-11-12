from verbecc.core.defs.types.data.verb_match_reason import VerbMatchReason


class VerbCatalogEntry:
    """
    Read-only VerbCatalog search result holding the matched verb metadata
    together with every reason the verb matched the query.

    A verb appears at most once in the search results even when it matches
    several reasons; all matching reasons are merged into ``reasons``.
    """

    def __init__(
        self,
        infinitive: str,
        translation_en: str,
        template: str,
        reasons: list[VerbMatchReason],
    ) -> None:
        self.infinitive = infinitive
        self.translation_en = translation_en
        self.template = template
        self.reasons = reasons

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, VerbCatalogEntry):
            return False
        return (
            self.infinitive == other.infinitive
            and self.translation_en == other.translation_en
            and self.template == other.template
            and self.reasons == other.reasons
        )

    def __repr__(self) -> str:
        return (
            "VerbCatalogEntry(infinitive={}, template={}, translation_en={}, "
            "reasons={})"
        ).format(self.infinitive, self.template, self.translation_en, self.reasons)

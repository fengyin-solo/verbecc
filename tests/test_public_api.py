from verbecc import CompleteConjugator
from verbecc import VerbCatalog
from verbecc.core import CompleteConjugator as CoreCompleteConjugator
from verbecc.core import VerbCatalog as CoreVerbCatalog
from verbecc.core.conjugator import CompleteConjugator as PackageCompleteConjugator
from verbecc.core.conjugator.complete_conjugator import CompleteConjugator as ImplementationCompleteConjugator
from verbecc.core.defs.types.data.verb_catalog import VerbCatalog as ImplementationVerbCatalog
from verbecc.core.defs.types.lang_code import LangCodeISO639_1 as Lang


def test_complete_conjugator_re_exports() -> None:
    assert CompleteConjugator is CoreCompleteConjugator
    assert CompleteConjugator is PackageCompleteConjugator
    assert CompleteConjugator is ImplementationCompleteConjugator


def test_verb_catalog_re_exports() -> None:
    assert VerbCatalog is CoreVerbCatalog
    assert VerbCatalog is ImplementationVerbCatalog


def test_public_complete_conjugator_conjugates() -> None:
    conjugator = CompleteConjugator(lang=Lang.fr)
    assert conjugator.conjugate("parler")


def test_public_verb_catalog_searches() -> None:
    catalog = VerbCatalog(lang=Lang.fr)
    results = catalog.search("manger")
    assert results
    assert results[0].infinitive == "manger"

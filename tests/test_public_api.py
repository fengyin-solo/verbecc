from verbecc import BatchConjugationResult
from verbecc import BatchConjugator
from verbecc import CompleteConjugator
from verbecc.core import BatchConjugationResult as CoreBatchConjugationResult
from verbecc.core import BatchConjugator as CoreBatchConjugator
from verbecc.core import CompleteConjugator as CoreCompleteConjugator
from verbecc.core.conjugator import BatchConjugationResult as PackageBatchConjugationResult
from verbecc.core.conjugator import BatchConjugator as PackageBatchConjugator
from verbecc.core.conjugator import CompleteConjugator as PackageCompleteConjugator
from verbecc.core.conjugator.batch_conjugation_result import BatchConjugationResult as ImplementationBatchConjugationResult
from verbecc.core.conjugator.batch_conjugator import BatchConjugator as ImplementationBatchConjugator
from verbecc.core.conjugator.complete_conjugator import CompleteConjugator as ImplementationCompleteConjugator
from verbecc.core.defs.types.lang_code import LangCodeISO639_1 as Lang


def test_complete_conjugator_re_exports() -> None:
    assert CompleteConjugator is CoreCompleteConjugator
    assert CompleteConjugator is PackageCompleteConjugator
    assert CompleteConjugator is ImplementationCompleteConjugator


def test_batch_conjugator_re_exports() -> None:
    assert BatchConjugator is CoreBatchConjugator
    assert BatchConjugator is PackageBatchConjugator
    assert BatchConjugator is ImplementationBatchConjugator


def test_batch_conjugation_result_re_exports() -> None:
    assert BatchConjugationResult is CoreBatchConjugationResult
    assert BatchConjugationResult is PackageBatchConjugationResult
    assert BatchConjugationResult is ImplementationBatchConjugationResult


def test_public_complete_conjugator_conjugates() -> None:
    conjugator = CompleteConjugator(lang=Lang.fr)
    assert conjugator.conjugate("parler")


def test_public_batch_conjugator_conjugates() -> None:
    conjugator = BatchConjugator(lang=Lang.fr)
    results = conjugator.conjugate(["parler"])
    assert len(results) == 1
    assert results[0].is_success()

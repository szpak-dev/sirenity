from collections.abc import Mapping

from pytest_bdd import given, scenarios, then, when

from sirenity import SirenDocument


class HarnessSteps:
    document: SirenDocument | None = None
    payload: Mapping[str, object] | None = None

    @staticmethod
    @given("a public Siren document", stacklevel=2)
    def public_siren_document() -> None:
        HarnessSteps.document = SirenDocument()

    @staticmethod
    @when("it is serialized", stacklevel=2)
    def serialized_siren_document() -> None:
        assert isinstance(HarnessSteps.document, SirenDocument)
        HarnessSteps.payload = HarnessSteps.document.model_dump(by_alias=True, mode="json", exclude_none=True)

    @staticmethod
    @then("the serialized value is an object", stacklevel=2)
    def serialized_value_is_an_object() -> None:
        assert isinstance(HarnessSteps.payload, Mapping)


scenarios("../features/harness.feature")

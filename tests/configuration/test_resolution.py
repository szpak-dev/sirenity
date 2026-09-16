from copy import deepcopy

import pytest

from sirenity.api import SirenityError, siren_configuration

from ..cases import ConfiguredCase
from ..support.applications.configuration import EXAMPLE_BOUNDED_OPENAPI


class TestConfigurationResolutionAttacks(ConfiguredCase):
    def test_adversarial_missing_openapi_provider_is_rejected(self) -> None:
        with pytest.raises(AttributeError):
            siren_configuration(
                openapi="tests.support.applications.configuration.EXAMPLE_MISSING_OPENAPI",
                policy="tests.support.collaborators.ExamplePolicy",
            )

    def test_adversarial_missing_policy_is_rejected(self) -> None:
        with pytest.raises(AttributeError):
            siren_configuration(
                openapi="tests.support.applications.configuration.EXAMPLE_ENTITY_OPENAPI",
                policy="tests.support.collaborators.ExampleMissingPolicy",
            )

    def test_invariant_invalid_contract_never_produces_a_partial_configuration(self) -> None:
        with pytest.raises(SirenityError, match="has_more property must be required"):
            siren_configuration(
                openapi="tests.support.applications.configuration.EXAMPLE_INVALID_OPENAPI",
                policy="tests.support.collaborators.ExamplePolicy",
            )

    def test_interruption_from_caller_policy_is_not_hidden(self) -> None:
        with pytest.raises(RuntimeError, match="example policy interrupted"):
            siren_configuration(
                openapi="tests.support.applications.configuration.EXAMPLE_ENTITY_OPENAPI",
                policy="tests.support.collaborators.ExampleInterruptedPolicy",
            )

    def test_cleanup_does_not_mutate_the_imported_openapi_mapping(self) -> None:
        original = deepcopy(EXAMPLE_BOUNDED_OPENAPI)

        siren_configuration(
            openapi="tests.support.applications.configuration.EXAMPLE_BOUNDED_OPENAPI",
            source_path="/api",
            public_path="/siren",
            policy="tests.support.collaborators.ExamplePolicy",
        )

        assert original == EXAMPLE_BOUNDED_OPENAPI

    def test_recovery_resolves_after_a_failed_policy_construction(self) -> None:
        with pytest.raises(RuntimeError):
            siren_configuration(
                openapi="tests.support.applications.configuration.EXAMPLE_ENTITY_OPENAPI",
                policy="tests.support.collaborators.ExampleInterruptedPolicy",
            )

        recovered = siren_configuration(
            openapi="tests.support.applications.configuration.EXAMPLE_ENTITY_OPENAPI",
            source_path="/api",
            public_path="/siren",
            policy="tests.support.collaborators.ExamplePolicy",
        )
        assert recovered.adapter().match("GET", "/siren/example_jobs/example-job-1") is not None


class TestConfigurationResolutionHappyPaths(ConfiguredCase):
    def test_mapping_provider_resolves_adapter_and_catalogue(self) -> None:
        configuration = siren_configuration(
            openapi="tests.support.applications.configuration.EXAMPLE_ENTITY_OPENAPI",
            source_path="/api",
            public_path="/siren",
            policy="tests.support.collaborators.ExamplePolicy",
        )

        assert configuration.adapter().match("GET", "/siren/example_jobs/example-job-1") is not None
        assert [tool.name for tool in configuration.catalogue().snapshot()] == ["get_example_job"]

    def test_one_configuration_retains_one_adapter_and_catalogue_lifecycle(self) -> None:
        configuration = siren_configuration(
            openapi="tests.support.applications.configuration.EXAMPLE_ENTITY_OPENAPI",
            source_path="/api",
            public_path="/siren",
            policy="tests.support.collaborators.ExamplePolicy",
        )

        assert configuration.adapter() is configuration.adapter()
        assert configuration.catalogue() is configuration.catalogue()

    def test_separate_configuration_calls_create_separate_lifecycles(self) -> None:
        first = siren_configuration(
            openapi="tests.support.applications.configuration.EXAMPLE_ENTITY_OPENAPI",
            source_path="/api",
            public_path="/siren",
            policy="tests.support.collaborators.ExamplePolicy",
        )
        second = siren_configuration(
            openapi="tests.support.applications.configuration.EXAMPLE_ENTITY_OPENAPI",
            source_path="/api",
            public_path="/siren",
            policy="tests.support.collaborators.ExamplePolicy",
        )

        assert first is not second
        assert first.adapter() is not second.adapter()
        assert first.catalogue() is not second.catalogue()

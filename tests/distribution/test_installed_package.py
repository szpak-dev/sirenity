import pytest

from ..cases import DistributionCase
from ..support.distribution import EXAMPLE_INSTALLED_PACKAGE


class TestInstalledPackageAttacks(DistributionCase):
    @pytest.mark.complete
    def test_adversarial_installed_caller_receives_public_continuation_error_and_recovers(self) -> None:
        result = EXAMPLE_INSTALLED_PACKAGE.run(
            """
import json
import os

from sirenity.api import SirenAdapterRequest, SirenityError, siren_adapter

adapter = siren_adapter(
    json.loads(os.environ["EXAMPLE_OPENAPI"]),
    source_path="/api",
    public_path="/siren",
    profiles=(),
)
try:
    adapter.respond(SirenAdapterRequest(
        operation_id="get_example_job",
        status=200,
        result={
            "example_job_id": "example-job-1",
            "example_state": "running",
            "has_more": True,
            "next_example_cursor": None,
        },
        base_url="https://api.example.test",
        path_values={"example_job_id": "example-job-1"},
    ))
except SirenityError:
    recovered = adapter.respond(SirenAdapterRequest(
        operation_id="get_example_job",
        status=200,
        result={
            "example_job_id": "example-job-1",
            "example_state": "complete",
            "has_more": False,
        },
        base_url="https://api.example.test",
        path_values={"example_job_id": "example-job-1"},
    ))
    assert recovered.continuations == ()
else:
    raise AssertionError("installed boundary accepted a null continuation")
print("example-recovered")
"""
        )

        assert result.returncode == 0, result.stderr
        assert result.stdout.strip() == "example-recovered"


class TestInstalledPackageHappyPaths(DistributionCase):
    @pytest.mark.complete
    def test_installed_caller_uses_the_public_bounded_continuation(self) -> None:
        result = EXAMPLE_INSTALLED_PACKAGE.run(
            """
import json
import os

from sirenity.api import SirenAdapterRequest, siren_adapter

adapter = siren_adapter(
    json.loads(os.environ["EXAMPLE_OPENAPI"]),
    source_path="/api",
    public_path="/siren",
    profiles=(),
)
response = adapter.respond(SirenAdapterRequest(
    operation_id="get_example_job",
    status=200,
    result={
        "example_job_id": "example-job-1",
        "example_state": "running",
        "has_more": True,
        "next_example_cursor": "example-cursor-2",
    },
    base_url="https://api.example.test",
    path_values={"example_job_id": "example-job-1"},
))
assert response.payload["links"][-1]["rel"] == ["next"]
assert response.continuations[0].operation_id == "get_example_job"
assert response.continuations[0].arguments == {
    "example_job_id": "example-job-1",
    "example_cursor": "example-cursor-2",
}
print("example-installed")
"""
        )

        assert result.returncode == 0, result.stderr
        assert result.stdout.strip() == "example-installed"

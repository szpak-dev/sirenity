from copy import deepcopy

import pytest

import sirenity

from ..functional.compiler.openapi_documents import SCHEMA


@pytest.mark.parametrize(
    ("openapi", "source_path", "public_path"),
    [
        ([], "/", "/"),
        (SCHEMA, "service", "/"),
        (SCHEMA, "/", "siren"),
    ],
)
def test_public_facade_rejects_invalid_mount_inputs(openapi, source_path, public_path):
    with pytest.raises(sirenity.SirenityError):
        sirenity.siren(openapi, source_path=source_path, public_path=public_path)


def test_public_facade_rejects_a_path_outside_the_source_mount():
    schema = deepcopy(SCHEMA)
    schema["paths"] = {f"/services{path}": item for path, item in schema["paths"].items()}

    with pytest.raises(sirenity.SirenityError):
        sirenity.siren(schema, source_path="/service", public_path="/siren")


def test_public_facade_remounts_paths_without_changing_the_caller_document():
    schema = deepcopy(SCHEMA)
    schema["paths"] = {f"/service{path}": item for path, item in schema["paths"].items()}
    original = deepcopy(schema)

    document = sirenity.siren(schema, source_path="/service/", public_path="/siren/").project(
        sirenity.SirenContext(base_url="https://api.example.com", scope="root")
    )

    assert document.model_dump(by_alias=True, mode="json", exclude_none=True)["links"] == [
        {"title": "Sirenity", "rel": ["self"], "href": "https://api.example.com/siren"},
        {"rel": ["collection"], "href": "https://api.example.com/siren/example_resources"},
    ]
    assert schema == original

import hashlib
import json
from importlib.resources import files

import sirenity
from sirenity import SirenAction, SirenField, SirenLink


class TestSirenSchemaProvenance:
    def test_vendored_schema_matches_the_pinned_source_and_digest(self):
        schema = files(sirenity).joinpath("contexts/shared/siren_schema/values/siren.schema.json")
        provenance = files(sirenity).joinpath("contexts/shared/siren_schema/values/siren.schema.provenance.json")

        assert json.loads(provenance.read_text()) == {
            "source_url": "https://github.com/kevinswiber/siren/blob/c29a87840407419d52c2acd742a1ad6a03ce80da/siren.schema.json",
            "source_revision": "c29a87840407419d52c2acd742a1ad6a03ce80da",
            "source_blob": "805711bc43d82a62e13f056bfa00791fe7b3b0fc",
            "vendored_sha256": "589aee71cca493ca398bb6246e0fb5dcab502c1f7fd2d2ae4ac6f776a51e564f",
        }
        assert hashlib.sha256(schema.read_bytes()).hexdigest() == json.loads(provenance.read_text())["vendored_sha256"]

    def test_public_vocabulary_and_defaults_resolve_the_pinned_schema(self):
        schema = files(sirenity).joinpath("contexts/shared/siren_schema/values/siren.schema.json")
        document = json.loads(schema.read_text())

        action_schema = SirenAction.model_json_schema()["properties"]
        field_schema = SirenField.model_json_schema()["properties"]
        relation_schema = SirenLink.model_json_schema()["properties"]["rel"]["items"]

        assert action_schema["method"] == {
            **document["definitions"]["Action"]["properties"]["method"],
            "title": "Method",
        }
        assert action_schema["type"] == {
            **document["definitions"]["MediaType"],
            "default": document["definitions"]["Action"]["properties"]["type"]["default"],
            "title": "Type",
        }
        assert SirenAction.default_media_type == document["definitions"]["Action"]["properties"]["type"]["default"]
        assert field_schema["type"] == {
            **document["definitions"]["Field"]["properties"]["type"],
            "title": "Type",
        }
        assert relation_schema == document["definitions"]["RelValue"]

from collections.abc import Mapping
from copy import deepcopy
from dataclasses import dataclass

from pydantic import JsonValue
from wireup import injectable

from sirenity.contexts.graph import SirenDelegatedInput, SirenInput

from ...request import SirenResponseContext


@injectable
@dataclass(frozen=True)
class SirenStructuredFormProfile:
    """Emit the versioned structured-form extension for delegated inputs.

    This opt-in profile adds the non-standard action member
    `https://modwire.dev/siren/structured-form/v1`. Its value has `version: "1"` and ordered
    `controls`. Each control exposes `name`, `location`, `required`, a resolved OpenAPI `schema`, and
    one versioned control URI. Body controls include `mediaType`; query, header, and cookie controls
    instead include materialized `style`, `explode`, and `allowReserved` serialization.

    Object and array controls use the `/object/v1` and `/array/v1` control URIs. Open JSON objects
    use `/json/v1`. Only delegated inputs are emitted, so ordinary official Siren fields are never
    duplicated. The profile walks actions recursively through embedded representations.
    """

    extension = "https://modwire.dev/siren/structured-form/v1"
    object_control = "https://modwire.dev/siren/controls/object/v1"
    array_control = "https://modwire.dev/siren/controls/array/v1"
    json_control = "https://modwire.dev/siren/controls/json/v1"

    def apply(
        self,
        operation_id: str,
        operation_input: SirenInput | None,
        operation_inputs: Mapping[str, SirenInput | None],
        document: Mapping[str, JsonValue],
        context: SirenResponseContext,
    ) -> Mapping[str, JsonValue]:
        return self.enrich(document, operation_inputs)

    def enrich(
        self,
        entity: Mapping[str, JsonValue],
        operation_inputs: Mapping[str, SirenInput | None],
    ) -> Mapping[str, JsonValue]:
        enriched = deepcopy(dict(entity))
        actions = enriched.get("actions")
        if isinstance(actions, list):
            enriched_actions = []
            for action in actions:
                enriched_action = dict(action)
                operation_input = operation_inputs.get(str(enriched_action.get("name")))
                if operation_input is not None and operation_input.delegated_inputs:
                    enriched_action[self.extension] = {
                        "version": "1",
                        "controls": [
                            self.control(delegated) for delegated in operation_input.delegated_inputs
                        ],
                    }
                enriched_actions.append(enriched_action)
            enriched["actions"] = enriched_actions
        entities = enriched.get("entities")
        if isinstance(entities, list):
            enriched["entities"] = [
                self.enrich(value, operation_inputs) if isinstance(value, dict) else value
                for value in entities
            ]
        return enriched

    def control(self, delegated: SirenDelegatedInput) -> Mapping[str, JsonValue]:
        definition = deepcopy(dict(delegated.definition))
        control_type = {
            "array": self.array_control,
            "object": self.object_control,
            "json": self.json_control,
        }[delegated.kind]
        control = {
            "name": delegated.name,
            "location": delegated.location,
            "required": delegated.required,
            "control": control_type,
            "schema": definition,
        }
        if delegated.media_type is not None:
            control["mediaType"] = delegated.media_type
        if delegated.location != "body":
            control["serialization"] = {
                "style": delegated.style,
                "explode": delegated.explode,
                "allowReserved": delegated.allow_reserved,
            }
        return control

import hashlib
import json
from dataclasses import dataclass

from wireup import injectable

from sirenity.contexts.runtime.adapter import SirenAdapter

from ..values import SirenMcpTool, SirenMcpToolCatalogue


@injectable
@dataclass(frozen=True)
class SirenMcpToolCatalogueService:
    """Project one deterministic MCP tool catalogue from an already compiled Siren graph."""

    def build(self, adapter: SirenAdapter) -> SirenMcpToolCatalogue:
        """Create the lifecycle-owned tool catalogue and its versioned canonical fingerprint."""

        tools = []
        for operation in sorted(adapter.engine.api.operations, key=lambda item: item.name):
            input = adapter.engine.operation_input(operation.name)
            properties = {}
            required = []
            definition = input.definition if input is not None else None
            body_properties = definition.get("properties", {}) if isinstance(definition, dict) else {}
            body_required = definition.get("required", ()) if isinstance(definition, dict) else ()
            if input is not None:
                for parameter in input.parameters:
                    properties[parameter.name] = parameter.definition
                    if parameter.required:
                        required.append(parameter.name)
            for name, schema in body_properties.items():
                if isinstance(schema, dict):
                    properties[name] = schema
                    if name in body_required:
                        required.append(name)
            if input is not None:
                for delegated in input.delegated_inputs:
                    if delegated.location == "body":
                        properties[delegated.name] = delegated.definition
                        if delegated.required:
                            required.append(delegated.name)
            schema = {
                "type": "object",
                "properties": properties,
                "additionalProperties": False,
            }
            if required:
                schema["required"] = sorted(set(required))
            tools.append(SirenMcpTool(
                name=operation.name,
                title=operation.title,
                description=operation.description,
                input_schema=schema,
            ))
        contract_version = "1"
        canonical = json.dumps(
            {
                "contract_version": contract_version,
                "tools": [tool.model_dump(mode="json") for tool in tools],
            },
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        )
        return SirenMcpToolCatalogue(
            contract_version=contract_version,
            fingerprint=hashlib.sha256(canonical.encode("utf-8")).hexdigest(),
            tools=tuple(tools),
        )

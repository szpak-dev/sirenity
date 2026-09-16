import hashlib
import json
from dataclasses import dataclass

from wireup import injectable

from ....graph import SirenApi, SirenInput
from ..values.catalogue import SirenMcpToolCatalogue
from ..values.tool import SirenMcpTool


@injectable
@dataclass(frozen=True)
class SirenMcpToolCatalogueService:
    def build(self, api: SirenApi) -> SirenMcpToolCatalogue:
        tools = []
        for operation in sorted(api.operations, key=lambda item: item.name):
            input = operation.input or SirenInput()
            properties = {}
            required = []
            body_properties = input.definition.get("properties", {})
            body_required = input.definition.get("required", ())
            for parameter in input.parameters:
                properties[parameter.name] = parameter.definition
                if parameter.required:
                    required.append(parameter.name)
            for name, schema in body_properties.items():
                properties[name] = schema
                if name in body_required:
                    required.append(name)
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
            tools.append(
                SirenMcpTool(
                    name=operation.name,
                    title=operation.title,
                    description=operation.description,
                    input_schema=schema,
                )
            )
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

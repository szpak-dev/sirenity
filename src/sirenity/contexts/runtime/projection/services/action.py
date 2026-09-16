from collections.abc import Mapping
from dataclasses import dataclass

from pydantic import JsonValue
from wireup import injectable

from ....graph import SirenApi, SirenField, SirenOperation, SirenResource
from ....shared import SirenityError, SirenScope
from ...document.values import field
from ...document.values.action import SirenAction
from ...document.values.field_value import SirenFieldValue
from ...request.values.context import SirenContext
from ...routing.contracts.href import SirenHrefService
from ..contracts.action import SirenActionDocumentService


@injectable(as_type=SirenActionDocumentService)
@dataclass(frozen=True)
class SirenDefaultActionDocumentService(SirenActionDocumentService):
    hrefs: SirenHrefService

    def actions(
        self,
        api: SirenApi,
        resource: SirenResource,
        scope: SirenScope,
        context: SirenContext,
        value: Mapping[str, JsonValue],
    ) -> list[SirenAction]:
        names = resource.collection_operations if scope == SirenScope.COLLECTION else resource.entity_operations
        operations = {operation.name: operation for operation in api.operations}
        return [
            self.action(operations[name], context, resource, value) for name in names if name in context.capabilities
        ]

    def action(
        self,
        operation: SirenOperation,
        context: SirenContext,
        resource: SirenResource | None,
        value: Mapping[str, JsonValue],
        include_query: bool = True,
    ) -> SirenAction:
        return SirenAction(
            name=operation.name,
            href=self.hrefs.href(operation.route.path, context, resource, value, include_query),
            method=operation.method,
            title=operation.title,
            type=operation.media_type,
            fields=tuple(
                field.SirenField(
                    name=definition.name,
                    type=definition.type,
                    title=definition.title,
                    value=(
                        tuple(
                            SirenFieldValue(
                                value=value,
                                selected=value == self.value(definition, operation, context, value),
                            )
                            for value in definition.values
                        )
                        if definition.values
                        else self.value(definition, operation, context, value)
                    ),
                )
                for definition in operation.fields
            )
            or None,
        )

    def value(
        self,
        definition: SirenField,
        operation: SirenOperation,
        context: SirenContext,
        source: Mapping[str, JsonValue],
    ) -> JsonValue:
        expression = context.action_bindings.get(operation.name, {}).get(definition.name)
        if expression is None:
            return definition.default
        prefix = "$response.body#"
        if not expression.startswith(prefix):
            raise SirenityError("Siren action binding runtime expression is unsupported")
        pointer = expression[len(prefix) :]
        value: JsonValue = dict(source)
        if pointer:
            if not pointer.startswith("/"):
                raise SirenityError("Siren action binding runtime expression is invalid")
            for token in pointer[1:].split("/"):
                token = token.replace("~1", "/").replace("~0", "~")
                value = value[token]
        if definition.values and value not in definition.values:
            raise SirenityError("Siren action binding value is incompatible with the target field")
        return value

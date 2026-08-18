from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from wireup import injectable

from sirenity.contexts.graph import SirenApi, SirenOperation, SirenResource
from sirenity.contexts.shared import SirenityError, SirenScope

from ...document import SirenAction, SirenField, SirenFieldValue
from ...request import SirenContext
from ...routing import SirenHrefService
from ..contracts import SirenActionDocumentService


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
        value: Mapping[str, Any],
    ) -> list[SirenAction]:
        names = resource.collection_operations if scope == SirenScope.COLLECTION else resource.entity_operations
        operations = {operation.name: operation for operation in api.operations}
        return [
            self.action(operations[name], context, resource, value)
            for name in names
            if name in context.capabilities
        ]

    def action(
        self,
        operation: SirenOperation,
        context: SirenContext,
        resource: SirenResource | None,
        value: Mapping[str, Any],
        include_query: bool = True,
    ) -> SirenAction:
        return SirenAction(
            name=operation.name,
            href=self.hrefs.href(operation.route.path, context, resource, value, include_query),
            method=operation.method,
            title=operation.title,
            type=operation.media_type,
            fields=tuple(
                SirenField(
                    name=field.name,
                    type=field.type,
                    title=field.title,
                    value=(
                        tuple(
                            SirenFieldValue(
                                value=value,
                                selected=value == self.value(field, operation, context, value),
                            )
                            for value in field.values
                        )
                        if field.values else self.value(field, operation, context, value)
                    ),
                )
                for field in operation.fields
            ) or None,
        )

    def value(self, field, operation: SirenOperation, context: SirenContext, source: Mapping[str, Any]):
        expression = context.action_bindings.get(operation.name, {}).get(field.name)
        if expression is None:
            return field.default
        prefix = "$response.body#"
        if not expression.startswith(prefix):
            raise SirenityError("Siren action binding runtime expression is unsupported")
        pointer = expression[len(prefix):]
        value: object = source
        if pointer:
            if not pointer.startswith("/"):
                raise SirenityError("Siren action binding runtime expression is invalid")
            for token in pointer[1:].split("/"):
                token = token.replace("~1", "/").replace("~0", "~")
                if not isinstance(value, Mapping) or token not in value:
                    raise SirenityError("Siren action binding runtime expression is missing")
                value = value[token]
        if isinstance(value, bool) or not isinstance(value, (str, int, float)):
            raise SirenityError("Siren action binding value is incompatible with the target field")
        if field.values and value not in field.values:
            raise SirenityError("Siren action binding value is incompatible with the target field")
        return value

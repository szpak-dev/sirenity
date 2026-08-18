from collections.abc import Mapping
from dataclasses import dataclass

from wireup import injectable

from sirenity.contexts.graph import (
    SirenApi,
    SirenDelegatedInput,
    SirenField,
    SirenInput,
    SirenOperation,
    SirenResource,
    SirenResponse,
    SirenResponseBinding,
    SirenResponseLink,
    SirenRoot,
    SirenRoute,
)
from sirenity.contexts.shared import SirenHttpMethod, SirenityError, SirenRelation, SirenScope

from ..state import SirenAssembly
from ..values import FieldDraft, OperationDraft, ResourceDraft


@injectable
@dataclass(frozen=True)
class SirenBuilder:
    """Build a validated Siren API graph from one operation's assembly state."""

    def build(self, assembly: SirenAssembly) -> SirenApi:
        resources = self.resource_index(assembly.resources)
        operations = self.operation_index(assembly.operations, resources)
        fields = self.field_index(assembly.fields, operations)
        resource_operations = self.resource_operation_index(operations)
        return SirenApi(
            root=SirenRoot(
                route=SirenRoute(path=assembly.root_path),
                title=assembly.root_title,
                version=assembly.root_version,
                operations=tuple(dict.fromkeys(assembly.root_operations)),
            ),
            resources=tuple(
                SirenResource(
                    reference=resource.reference,
                    name=resource.name,
                    resource_class=resource.resource_class,
                    title=self.resource_title(
                        resource, operations, SirenScope.ENTITY),
                    collection_title=self.resource_title(
                        resource, operations, SirenScope.COLLECTION),
                    identifier=resource.identifier,
                    collection=SirenRoute(path=resource.collection_path),
                    entity=SirenRoute(
                        path=resource.entity_path) if resource.entity_path else None,
                    collection_operations=resource_operations.get(
                        (resource.reference, SirenScope.COLLECTION), ()),
                    entity_operations=resource_operations.get(
                        (resource.reference, SirenScope.ENTITY), ()),
                )
                for resource in resources.values()
            ),
            operations=tuple(
                SirenOperation(
                    name=operation.name,
                    resource=operation.resource,
                    scope=operation.scope,
                    method=operation.method,
                    route=SirenRoute(path=operation.path),
                    title=operation.title,
                    description=operation.description,
                    media_type=operation.media_type,
                    fields=tuple(
                        SirenField(
                            name=item.name,
                            type=item.type,
                            values=item.values,
                            title=item.title,
                            default=item.default,
                        )
                        for item in fields.get(operation.name, ())
                    ),
                    input=SirenInput(
                        media_type=operation.input.media_type,
                        definition=operation.input.definition,
                        official_fields=operation.input.official_fields,
                        delegated_inputs=tuple(
                            SirenDelegatedInput(
                                name=item.name,
                                location=item.location,
                                kind=item.kind,
                                required=item.required,
                                media_type=item.media_type,
                                style=item.style,
                                explode=item.explode,
                                allow_reserved=item.allow_reserved,
                                definition=item.definition,
                            )
                            for item in operation.input.delegated_inputs
                        ),
                    ) if operation.input else None,
                    responses=tuple(
                        SirenResponse(
                            status=response.status,
                            media_type=response.media_type,
                            shape=response.shape,
                            definition=response.definition,
                            bindings=self.response_bindings(response, fields),
                            links=tuple(
                                SirenResponseLink(
                                    operation=self.link_operation(
                                        link, operations),
                                    parameters=link.parameters,
                                    rel=tuple(SirenRelation.validate(value)
                                              for value in link.rel),
                                    scope=link.scope,
                                )
                                for link in response.links
                            ),
                        )
                        for response in operation.responses
                    ),
                )
                for operation in operations.values()
            ),
        )

    def response_bindings(
        self, response, fields: Mapping[str, tuple[FieldDraft, ...]]
    ) -> tuple[SirenResponseBinding, ...]:
        values = []
        for binding in response.bindings:
            operation_fields = {field.name for field in fields.get(binding.operation, ())}
            if not operation_fields:
                raise SirenityError(
                    f"OpenAPI response action binding targets unknown or delegated operation field: {binding.operation}"
                )
            if not set(binding.fields).issubset(operation_fields):
                raise SirenityError(
                    f"OpenAPI response action binding targets an unknown or delegated field: {binding.operation}"
                )
            if any(not expression.startswith("$response.body#") for expression in binding.fields.values()):
                raise SirenityError("OpenAPI response action binding runtime expression is unsupported")
            values.append(SirenResponseBinding(operation=binding.operation, fields=binding.fields))
        return tuple(values)

    def resource_title(
        self, resource: ResourceDraft, operations: Mapping[str, OperationDraft], scope: SirenScope
    ) -> str | None:
        candidates: list[tuple[int, int, str]] = []
        for operation in operations.values():
            if operation.resource != resource.reference:
                continue
            exact_collection = operation.path == resource.collection_path
            exact_entity = resource.entity_path is not None and operation.path == resource.entity_path
            if not exact_collection and not exact_entity:
                continue
            for response in operation.responses:
                if not response.status.startswith("2") or response.definition is None:
                    continue
                definition = response.definition
                title: object = None
                priority = 0
                if scope == SirenScope.COLLECTION and exact_collection and response.shape == "array":
                    priority = 0 if operation.method == SirenHttpMethod.GET else 1
                    title = definition.get("title")
                    if title == "Response" or (
                        isinstance(title, str) and title.startswith(
                            "Response ")
                    ):
                        title = None
                elif scope == SirenScope.ENTITY and exact_entity and response.shape == "object":
                    priority = 0 if operation.method == SirenHttpMethod.GET else 2
                    title = definition.get("title")
                elif scope == SirenScope.ENTITY and exact_collection and response.shape == "array":
                    priority = 1 if operation.method == SirenHttpMethod.GET else 3
                    items = definition.get("items")
                    title = items.get("title") if isinstance(
                        items, Mapping) else None
                if isinstance(title, str) and title:
                    candidates.append((priority, len(candidates), title))
        return min(candidates)[2] if candidates else None

    def link_operation(self, link, operations: Mapping[str, OperationDraft]) -> str:
        if link.operation_id is not None:
            operation = operations.get(link.operation_id)
            if operation is None:
                raise SirenityError(
                    f"OpenAPI response link references unknown operation: {link.operation_id}"
                )
            target = operation
        else:
            reference = link.operation_ref
            if reference is None or "#" not in reference:
                raise SirenityError(
                    f"OpenAPI response link operationRef is invalid: {reference}")
            path, method = reference.rsplit("#", 1)
            matches = [
                operation for operation in operations.values()
                if operation.path == path and operation.method.value.lower() == method
            ]
            if len(matches) != 1:
                raise SirenityError(
                    f"OpenAPI response link operationRef is unknown: {reference}")
            target = matches[0]
        if target.resource is None or target.scope != link.scope:
            raise SirenityError(
                "OpenAPI response link target does not match declared Siren scope")
        required = {
            segment[1:-1]
            for segment in target.path.split("/")
            if segment.startswith("{") and segment.endswith("}")
        }
        supplied = {
            name[len("path."):] if name.startswith("path.") else name
            for name in link.parameters
        }
        if supplied != required:
            raise SirenityError(
                "OpenAPI response link parameters do not match the target route")
        for expression in link.parameters.values():
            if not expression.startswith("$response.body#"):
                raise SirenityError(
                    f"OpenAPI response link runtime expression is unsupported: {expression}"
                )
            pointer = expression[len("$response.body#"):]
            if pointer and not pointer.startswith("/"):
                raise SirenityError(
                    f"OpenAPI response link runtime expression is invalid: {expression}"
                )
        return target.name

    def resource_index(self, resources: list[ResourceDraft]) -> dict[str, ResourceDraft]:
        index: dict[str, ResourceDraft] = {}
        for resource in resources:
            if resource.reference in index:
                raise SirenityError(
                    f"Siren resource already exists: {resource.reference}")
            index[resource.reference] = resource
        return index

    def operation_index(
        self, operations: list[OperationDraft], resources: Mapping[str, ResourceDraft]
    ) -> dict[str, OperationDraft]:
        index: dict[str, OperationDraft] = {}
        for operation in operations:
            if operation.name in index:
                raise SirenityError(
                    f"Siren operation already exists: {operation.name}")
            if operation.scope == SirenScope.ROOT:
                if operation.resource is not None:
                    raise SirenityError(
                        f"Siren root operation {operation.name!r} cannot reference a resource")
            else:
                resource = resources.get(operation.resource)
                if resource is None:
                    raise SirenityError(
                        f"Siren operation {operation.name!r} references unknown resource {operation.resource!r}"
                    )
                self.validate_operation_path(operation, resource)
            index[operation.name] = operation
        return index

    def validate_operation_path(self, operation: OperationDraft, resource: ResourceDraft) -> None:
        if operation.scope == SirenScope.ENTITY:
            if resource.entity_path is None:
                raise SirenityError(
                    f"Siren resource {resource.name!r} has no entity path")
            valid = operation.path == resource.entity_path or operation.path.startswith(
                f"{resource.entity_path}/")
        else:
            valid = operation.path == resource.collection_path or operation.path.startswith(
                f"{resource.collection_path}/"
            )
            if resource.entity_path and (
                operation.path == resource.entity_path or operation.path.startswith(
                    f"{resource.entity_path}/")
            ):
                valid = False
        if not valid:
            raise SirenityError(
                f"Siren operation {operation.name!r} path {operation.path!r} does not belong to "
                f"{operation.scope} scope of resource {resource.name!r}"
            )

    def field_index(
        self, fields: list[FieldDraft], operations: Mapping[str, OperationDraft]
    ) -> dict[str, tuple[FieldDraft, ...]]:
        index: dict[str, list[FieldDraft]] = {}
        names: dict[str, set[str]] = {}
        for item in fields:
            if item.operation not in operations:
                raise SirenityError(
                    f"Siren field {item.name!r} references unknown operation {item.operation!r}")
            operation_fields = index.setdefault(item.operation, [])
            operation_names = names.setdefault(item.operation, set())
            if item.name in operation_names:
                raise SirenityError(
                    f"Siren operation {item.operation!r} has duplicate field {item.name!r}")
            operation_fields.append(item)
            operation_names.add(item.name)
        return {operation: tuple(items) for operation, items in index.items()}

    def resource_operation_index(
        self, operations: Mapping[str, OperationDraft]
    ) -> dict[tuple[str, SirenScope], tuple[str, ...]]:
        index: dict[tuple[str, SirenScope], list[str]] = {}
        for operation in operations.values():
            if operation.resource is not None:
                index.setdefault((operation.resource, operation.scope), []).append(
                    operation.name)
        return {key: tuple(names) for key, names in index.items()}

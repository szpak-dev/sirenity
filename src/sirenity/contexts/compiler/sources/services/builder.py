from collections.abc import Mapping
from dataclasses import dataclass
from typing import Literal

from wireup import injectable

from .... import graph, shared
from ....graph.model import (
    SirenContinuation,
    SirenContinuationKind,
    SirenContinuationParameter,
)
from ..values.normalized import NormalizedOpenApi
from ..values.operation_draft import OperationDraft
from ..values.resource import Resource
from ..values.response_continuation import ResponseContinuationDraft, ResponseOperationTarget
from ..values.response_draft import ResponseDraft
from ..values.response_link_draft import ResponseLinkDraft


@injectable
@dataclass(frozen=True)
class SirenBuilder:
    def build(self, normalized: NormalizedOpenApi) -> graph.SirenApi:
        resources = self.resource_index(normalized.resources)
        operations = self.operation_index(normalized.operations, resources)
        fields = {name: operation.fields for name, operation in operations.items()}
        resource_operations = self.resource_operation_index(operations)
        return graph.SirenApi(
            root=graph.SirenRoot(
                route=graph.SirenRoute(path=normalized.root_path),
                title=normalized.root_title,
                version=normalized.root_version,
                operations=tuple(dict.fromkeys(normalized.root_operations)),
            ),
            resources=tuple(
                graph.SirenResource(
                    reference=resource.reference,
                    name=resource.name,
                    resource_class=resource.resource_class,
                    path_bindings=resource.path_bindings,
                    title=self.resource_title(resource, operations),
                    identifier=resource.identifier,
                    collection=graph.SirenRoute(path=resource.collection_path),
                    entity=graph.SirenRoute(path=resource.entity_path) if resource.entity_path else None,
                    collection_operations=resource_operations.get(
                        (resource.reference, shared.SirenScope.COLLECTION), ()
                    ),
                    entity_operations=resource_operations.get((resource.reference, shared.SirenScope.ENTITY), ()),
                )
                for resource in resources.values()
            ),
            operations=tuple(
                graph.SirenOperation(
                    name=operation.name,
                    resource=operation.resource,
                    scope=operation.scope,
                    method=operation.method,
                    route=graph.SirenRoute(path=operation.path),
                    source_path=operation.source_path,
                    title=operation.title,
                    description=operation.description,
                    media_type=operation.media_type,
                    fields=operation.fields,
                    input=operation.input,
                    responses=tuple(
                        graph.SirenResponse(
                            status=response.status,
                            media_type=response.media_type,
                            shape=response.shape,
                            definition=response.definition,
                            bindings=self.response_bindings(response, fields),
                            links=self.response_links(operation, response, operations, resources),
                            continuations=self.response_continuations(operation, response, operations),
                        )
                        for response in operation.responses
                    ),
                )
                for operation in operations.values()
            ),
        )

    def response_links(
        self,
        operation: OperationDraft,
        response: ResponseDraft,
        operations: Mapping[str, OperationDraft],
        resources: Mapping[str, Resource],
    ) -> tuple[graph.SirenResponseLink, ...]:
        declared: list[graph.SirenResponseLink] = []
        for link in response.links:
            target = self.link_operation(link, operations)
            scope = link.scope
            self.validate_link(operation, link, target, scope)
            declared.append(
                graph.SirenResponseLink(
                    operation=target.name,
                    parameters=link.parameters,
                    rel=tuple(shared.SirenRelation.validate(value) for value in link.rel),
                    scope=scope,
                )
            )
        declared_links = tuple(declared)
        declared_targets = {(link.operation, link.scope) for link in declared_links}
        derived = tuple(
            link
            for link in self.nested_collection_links(operation, response, operations, resources)
            if (link.operation, link.scope) not in declared_targets
        )
        return (*declared_links, *derived)

    def response_continuations(
        self,
        source: OperationDraft,
        response: ResponseDraft,
        operations: Mapping[str, OperationDraft],
    ) -> tuple[SirenContinuation, ...]:
        continuations: list[SirenContinuation] = []
        for draft in response.continuations:
            target = self.continuation_operation(draft.target, operations)
            self.validate_continuation(source, draft, target)
            continuations.append(
                SirenContinuation(
                    operation=target.name,
                    kind=draft.kind,
                    parameters=self.continuation_parameters(source, draft, target),
                )
            )
        return tuple(continuations)

    def continuation_operation(
        self,
        target: ResponseOperationTarget,
        operations: Mapping[str, OperationDraft],
    ) -> OperationDraft:
        if target.kind == "operation_id":
            operation = operations.get(target.value)
            if operation is None:
                raise shared.SirenityError(f"OpenAPI continuation references unknown operation: {target.value}")
            return operation
        return self.operation_by_reference(target.value, operations, "continuation")

    def validate_continuation(
        self,
        source: OperationDraft,
        continuation: ResponseContinuationDraft,
        target: OperationDraft,
    ) -> None:
        if not continuation.parameters:
            if continuation.kind == SirenContinuationKind.PAGINATION:
                raise shared.SirenityError(
                    "OpenAPI pagination continuation must target the same collection GET operation"
                )
            raise shared.SirenityError("OpenAPI bounded continuation parameters are invalid")
        if continuation.kind == SirenContinuationKind.PAGINATION and (
            source.name != target.name
            or target.resource is None
            or target.method != shared.SirenHttpMethod.GET
            or target.scope != shared.SirenScope.COLLECTION
        ):
            raise shared.SirenityError("OpenAPI pagination continuation must target the same collection GET operation")

    def continuation_parameters(
        self,
        source: OperationDraft,
        continuation: ResponseContinuationDraft,
        target: OperationDraft,
    ) -> tuple[SirenContinuationParameter, ...]:
        required_path = set(self.path_parameters(target.path))
        inherited_path = set(self.path_parameters(source.path))
        target_parameters = target.input.parameters if target.input is not None else ()
        query_parameters = {parameter.name for parameter in target_parameters if parameter.location == "query"}
        inherited_query = (
            {parameter.name for parameter in source.input.parameters if parameter.location == "query"}
            if source.input is not None
            else set()
        )
        unsupported_required = {
            parameter.name
            for parameter in target_parameters
            if parameter.required and parameter.location in {"header", "cookie"}
        }
        if target.input is not None:
            definition = target.input.definition
            body_required = set(definition.get("required", ()))
            body_required.update(
                delegated.name
                for delegated in target.input.delegated_inputs
                if delegated.location == "body" and delegated.required
            )
            unsupported_required.update(body_required)
        if unsupported_required:
            raise shared.SirenityError("OpenAPI continuation target has required header, cookie, or body inputs")
        required_query = {
            parameter.name for parameter in target_parameters if parameter.required and parameter.location == "query"
        }
        compiled: list[SirenContinuationParameter] = []
        supplied_path: set[str] = set()
        supplied_query: set[str] = set()
        supplied: set[tuple[str, str]] = set()
        for parameter in continuation.parameters:
            name = parameter.name
            location: Literal["path", "query"]
            if name.startswith("path."):
                location = "path"
                name = name[len("path.") :]
                if name not in required_path:
                    raise shared.SirenityError(
                        f"OpenAPI response link parameter does not match the target operation: {parameter.name}"
                    )
            elif name.startswith("query."):
                location = "query"
                name = name[len("query.") :]
                if name not in query_parameters:
                    raise shared.SirenityError(
                        f"OpenAPI response link parameter does not match the target operation: {parameter.name}"
                    )
            elif name in required_path:
                location = "path"
            elif name in query_parameters:
                location = "query"
            else:
                raise shared.SirenityError(
                    f"OpenAPI response link parameter does not match the target operation: {name}"
                )
            key = (location, name)
            if key in supplied:
                raise shared.SirenityError(f"OpenAPI continuation maps the target argument more than once: {name}")
            supplied.add(key)
            if location == "path":
                supplied_path.add(name)
            else:
                supplied_query.add(name)
            compiled.append(
                SirenContinuationParameter(
                    name=name,
                    location=location,
                    pointer=self.response_pointer(parameter.expression),
                )
            )
        if continuation.kind == SirenContinuationKind.PAGINATION:
            if not supplied_query or (supplied_path and supplied_path != required_path):
                raise shared.SirenityError(
                    "OpenAPI pagination continuation must target the same collection GET operation"
                )
        elif not required_path.issubset(supplied_path | inherited_path):
            raise shared.SirenityError("OpenAPI bounded continuation parameters do not satisfy the target route")
        if not required_query.issubset(supplied_query | inherited_query):
            raise shared.SirenityError("OpenAPI continuation parameters do not satisfy required target query inputs")
        return tuple(compiled)

    def response_pointer(self, expression: str) -> tuple[str, ...]:
        prefix = "$response.body#/"
        if not expression.startswith(prefix):
            raise shared.SirenityError(f"OpenAPI continuation runtime expression is unsupported: {expression}")
        return tuple(token.replace("~1", "/").replace("~0", "~") for token in expression[len(prefix) :].split("/"))

    def nested_collection_links(
        self,
        operation: OperationDraft,
        response: ResponseDraft,
        operations: Mapping[str, OperationDraft],
        resources: Mapping[str, Resource],
    ) -> tuple[graph.SirenResponseLink, ...]:
        if (
            operation.resource is None
            or operation.method
            not in {
                shared.SirenHttpMethod.GET,
                shared.SirenHttpMethod.POST,
                shared.SirenHttpMethod.PUT,
                shared.SirenHttpMethod.PATCH,
            }
            or not response.status.startswith("2")
            or response.shape != "object"
            or response.definition is None
        ):
            return ()
        resource = resources[operation.resource]
        if resource.entity_path is None or operation.path not in {
            resource.collection_path,
            resource.entity_path,
        }:
            return ()
        parameters = self.path_parameters(resource.entity_path)
        properties = response.definition.get("properties")
        if not parameters or properties is None:
            return ()
        response_bindings = {}
        for name in parameters:
            candidates = resource.path_bindings[name]
            available = tuple(candidate for candidate in candidates if candidate in properties)
            if not available:
                return ()
            response_bindings[name] = available[0]
        links = []
        for nested in resources.values():
            prefix = f"{resource.entity_path}/"
            if (
                nested.reference == resource.reference
                or not nested.collection_path.startswith(prefix)
                or "/" in nested.collection_path[len(prefix) :]
                or self.path_parameters(nested.collection_path) != parameters
            ):
                continue
            targets = [
                candidate
                for candidate in operations.values()
                if candidate.resource == nested.reference
                and candidate.scope == shared.SirenScope.COLLECTION
                and candidate.method == shared.SirenHttpMethod.GET
                and candidate.path == nested.collection_path
            ]
            if len(targets) != 1:
                continue
            links.append(
                graph.SirenResponseLink(
                    operation=targets[0].name,
                    parameters={
                        f"path.{name}": f"$response.body#/{self.pointer_token(response_bindings[name])}"
                        for name in parameters
                    },
                    rel=(shared.SirenRelation.validate("collection"),),
                    scope=shared.SirenScope.COLLECTION,
                )
            )
        return tuple(links)

    def path_parameters(self, path: str) -> tuple[str, ...]:
        return tuple(segment[1:-1] for segment in path.split("/") if segment.startswith("{") and segment.endswith("}"))

    def pointer_token(self, value: str) -> str:
        return value.replace("~", "~0").replace("/", "~1")

    def response_bindings(
        self, response: ResponseDraft, fields: Mapping[str, tuple[graph.SirenField, ...]]
    ) -> tuple[graph.SirenResponseBinding, ...]:
        values = []
        for binding in response.bindings:
            operation_fields = {field.name for field in fields.get(binding.operation, ())}
            if not operation_fields:
                raise shared.SirenityError(
                    f"OpenAPI response action binding targets unknown or delegated operation field: {binding.operation}"
                )
            if not set(binding.fields).issubset(operation_fields):
                raise shared.SirenityError(
                    f"OpenAPI response action binding targets an unknown or delegated field: {binding.operation}"
                )
            if any(not expression.startswith("$response.body#") for expression in binding.fields.values()):
                raise shared.SirenityError("OpenAPI response action binding runtime expression is unsupported")
            values.append(
                graph.SirenResponseBinding(
                    operation=binding.operation,
                    fields=binding.fields,
                )
            )
        return tuple(values)

    def resource_title(self, resource: Resource, operations: Mapping[str, OperationDraft]) -> str | None:
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
                priority = 0
                if exact_entity and response.shape == "object":
                    priority = 0 if operation.method == shared.SirenHttpMethod.GET else 2
                    title = definition["title"]
                elif exact_collection and response.shape == "array":
                    priority = 1 if operation.method == shared.SirenHttpMethod.GET else 3
                    title = definition["items"]["title"]
                elif exact_collection and any(
                    continuation.kind == SirenContinuationKind.PAGINATION for continuation in response.continuations
                ):
                    priority = 1 if operation.method == shared.SirenHttpMethod.GET else 3
                    title = definition["properties"][self.page_items(response)]["items"]["title"]
                else:
                    continue
                candidates.append((priority, len(candidates), title))
        return min(candidates)[2] if candidates else None

    def page_items(self, response: ResponseDraft) -> str:
        properties = response.definition["properties"]
        return next(
            name
            for name, value in properties.items()
            if (value.get("type") == "array" and value["items"].get("type") == "object")
        )

    def link_operation(self, link: ResponseLinkDraft, operations: Mapping[str, OperationDraft]) -> OperationDraft:
        if link.operation_id is not None:
            operation = operations.get(link.operation_id)
            if operation is None:
                raise shared.SirenityError(f"OpenAPI response link references unknown operation: {link.operation_id}")
            target = operation
        else:
            reference = link.operation_ref
            if reference is None:
                raise shared.SirenityError("OpenAPI response link operationRef is invalid")
            target = self.operation_by_reference(reference, operations, "response link")
        return target

    def operation_by_reference(
        self,
        reference: str,
        operations: Mapping[str, OperationDraft],
        source: str,
    ) -> OperationDraft:
        if "#" not in reference:
            raise shared.SirenityError(f"OpenAPI {source} operationRef is invalid: {reference}")
        path, method = reference.rsplit("#", 1)
        matches = [
            operation
            for operation in operations.values()
            if operation.path == path and operation.method.value.lower() == method
        ]
        if len(matches) != 1:
            raise shared.SirenityError(f"OpenAPI {source} operationRef is unknown: {reference}")
        return matches[0]

    def validate_link(
        self,
        source: OperationDraft,
        link: ResponseLinkDraft,
        target: OperationDraft,
        scope: shared.SirenScope,
    ) -> None:
        pagination = "next" in link.rel
        if pagination:
            if (
                source.name != target.name
                or target.resource is None
                or target.method != shared.SirenHttpMethod.GET
                or target.scope != shared.SirenScope.COLLECTION
            ):
                raise shared.SirenityError("OpenAPI next response link must continue the same collection GET operation")
        elif target.resource is None or target.scope != scope:
            raise shared.SirenityError("OpenAPI response link target does not match declared Siren scope")
        required_path = {
            segment[1:-1] for segment in target.path.split("/") if segment.startswith("{") and segment.endswith("}")
        }
        query_parameters = (
            {parameter.name for parameter in target.input.parameters if parameter.location == "query"}
            if target.input is not None
            else set()
        )
        supplied_path = set()
        supplied_query = set()
        for name in link.parameters:
            if name.startswith("path."):
                supplied_path.add(name[len("path.") :])
            elif name.startswith("query."):
                supplied_query.add(name[len("query.") :])
            elif name in required_path:
                supplied_path.add(name)
            elif name in query_parameters:
                supplied_query.add(name)
            else:
                raise shared.SirenityError(
                    f"OpenAPI response link parameter does not match the target operation: {name}"
                )
        if pagination and (not supplied_query or (supplied_path and supplied_path != required_path)):
            raise shared.SirenityError("OpenAPI next response link must continue the same collection GET operation")
        if not pagination and supplied_path != required_path:
            raise shared.SirenityError("OpenAPI response link parameters do not match the target route")
        for expression in link.parameters.values():
            if not expression.startswith("$response.body#"):
                raise shared.SirenityError(f"OpenAPI response link runtime expression is unsupported: {expression}")
            pointer = expression[len("$response.body#") :]
            if pointer and not pointer.startswith("/"):
                raise shared.SirenityError(f"OpenAPI response link runtime expression is invalid: {expression}")

    def resource_index(self, resources: tuple[Resource, ...]) -> dict[str, Resource]:
        index: dict[str, Resource] = {}
        for resource in resources:
            if resource.reference in index:
                raise shared.SirenityError(f"Siren resource already exists: {resource.reference}")
            index[resource.reference] = resource
        return index

    def operation_index(
        self, operations: tuple[OperationDraft, ...], resources: Mapping[str, Resource]
    ) -> dict[str, OperationDraft]:
        index: dict[str, OperationDraft] = {}
        for operation in operations:
            if operation.name in index:
                raise shared.SirenityError(f"Siren operation already exists: {operation.name}")
            if operation.scope == shared.SirenScope.ROOT:
                if operation.resource is not None:
                    raise shared.SirenityError(f"Siren root operation {operation.name!r} cannot reference a resource")
            else:
                resource = resources.get(operation.resource)
                if resource is None:
                    raise shared.SirenityError(
                        f"Siren operation {operation.name!r} references unknown resource {operation.resource!r}"
                    )
                self.validate_operation_path(operation, resource)
            index[operation.name] = operation
        return index

    def validate_operation_path(self, operation: OperationDraft, resource: Resource) -> None:
        if operation.scope == shared.SirenScope.ENTITY:
            if resource.entity_path is None:
                raise shared.SirenityError(f"Siren resource {resource.name!r} has no entity path")
            valid = operation.path == resource.entity_path or operation.path.startswith(f"{resource.entity_path}/")
        else:
            valid = operation.path == resource.collection_path or operation.path.startswith(
                f"{resource.collection_path}/"
            )
            if resource.entity_path and (
                operation.path == resource.entity_path or operation.path.startswith(f"{resource.entity_path}/")
            ):
                valid = False
        if not valid:
            raise shared.SirenityError(
                f"Siren operation {operation.name!r} path {operation.path!r} does not belong to "
                f"{operation.scope} scope of resource {resource.name!r}"
            )

    def resource_operation_index(
        self, operations: Mapping[str, OperationDraft]
    ) -> dict[tuple[str, shared.SirenScope], tuple[str, ...]]:
        index: dict[tuple[str, shared.SirenScope], list[str]] = {}
        for operation in operations.values():
            if operation.resource is not None:
                index.setdefault((operation.resource, operation.scope), []).append(operation.name)
        return {key: tuple(names) for key, names in index.items()}

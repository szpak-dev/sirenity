from collections.abc import Mapping
from dataclasses import dataclass

from wireup import injectable

from sirenity.contexts.graph import SirenApi, SirenOperation, SirenResource, SirenResponse
from sirenity.contexts.shared import SirenityError, SirenRepresentation, SirenScope

from ...document import SirenDocument, SirenLink
from ...request import SirenContext, SirenRelationship, SirenResponseContext
from ...routing import SirenHrefService
from .projection import SirenProjectionService


@injectable
@dataclass(frozen=True)
class SirenResponseProjectionService:
    projection: SirenProjectionService
    hrefs: SirenHrefService

    def project(self, api: SirenApi, context: SirenResponseContext) -> SirenDocument:
        operation = self.operation(api, context.operation_id)
        response = self.response(operation, context)
        resource = self.resource(api, operation)
        self.validate_result(response, context.result)
        if context.status >= 400:
            return self.error(operation, resource, context)
        if context.representation == SirenRepresentation.ROOT and response.shape != "object":
            raise SirenityError(
                "Siren root response requires an OpenAPI object response")
        if response.shape == "empty":
            return self.empty(operation, resource, context)
        if response.shape == "array":
            if context.representation not in {None, SirenRepresentation.COLLECTION}:
                raise SirenityError(
                    "OpenAPI array response requires collection representation")
            return self.collection(api, resource, context, response)
        if self.paginated(response):
            if context.representation not in {None, SirenRepresentation.COLLECTION}:
                raise SirenityError(
                    "OpenAPI paginated response requires collection representation")
            if resource is None:
                raise SirenityError(
                    "OpenAPI paginated response requires a collection resource")
            return self.page(api, operation, resource, context, response)
        representation = context.representation
        if (
            representation is None
            and operation.scope == SirenScope.ROOT
            and operation.route == api.root.route
        ):
            representation = SirenRepresentation.ROOT
        if representation == SirenRepresentation.ROOT:
            return self.root(api, operation, context)
        if (
            representation is None
            and resource is not None
            and operation.route in {resource.collection, resource.entity}
        ):
            representation = SirenRepresentation.ENTITY
        if representation is None:
            representation = SirenRepresentation.COMMAND
        if representation == SirenRepresentation.ENTITY:
            return self.entity(api, resource, context, response)
        if representation == SirenRepresentation.COMMAND:
            return self.command(api, operation, resource, context, response)
        raise SirenityError(
            "OpenAPI object response cannot use collection representation")

    def root(
        self, api: SirenApi, operation: SirenOperation, context: SirenResponseContext
    ) -> SirenDocument:
        if operation.scope != SirenScope.ROOT or not isinstance(context.result, Mapping):
            raise SirenityError(
                "Siren root response requires a root operation and mapping result")
        request = SirenContext(
            base_url=context.base_url,
            scope=SirenScope.ROOT,
            title=context.title,
            value=context.result,
            path_values=context.path_values,
            query=context.query,
            capabilities=context.capabilities,
        )
        return self.projection.project(api, request)

    def operation(self, api: SirenApi, operation_id: str) -> SirenOperation:
        matches = [
            operation for operation in api.operations if operation.name == operation_id]
        if len(matches) != 1:
            raise SirenityError(
                f"Siren response references unknown operation: {operation_id}")
        return matches[0]

    def response(self, operation: SirenOperation, context: SirenResponseContext) -> SirenResponse:
        candidates = list(self.candidates(operation, context))
        if context.media_type is None and len(candidates) > 1:
            json_candidates = [
                response for response in candidates if response.media_type == "application/json"]
            candidates = json_candidates if len(
                json_candidates) == 1 else candidates
        if len(candidates) != 1:
            raise SirenityError(
                f"Siren response requires exactly one status and media type match: "
                f"{operation.name} {context.status}"
            )
        return candidates[0]

    def has_response(self, api: SirenApi, context: SirenResponseContext) -> bool:
        operation = self.operation(api, context.operation_id)
        return bool(self.candidates(operation, context))

    def candidates(
        self, operation: SirenOperation, context: SirenResponseContext
    ) -> tuple[SirenResponse, ...]:
        exact = [response for response in operation.responses if response.status == str(
            context.status)]
        ranged = [
            response
            for response in operation.responses
            if len(response.status) == 3
            and response.status[0] == str(context.status)[0]
            and response.status[1:].upper() == "XX"
        ]
        defaults = [
            response for response in operation.responses if response.status == "default"]
        candidates = exact or ranged or defaults
        if context.media_type is not None:
            candidates = [
                response for response in candidates if response.media_type == context.media_type]
        return tuple(candidates)

    def project_error(
        self, api: SirenApi, context: SirenResponseContext, request_url: str | None = None
    ) -> SirenDocument:
        operation = self.operation(api, context.operation_id)
        resource = self.resource(api, operation)
        return self.error(operation, resource, context, request_url)

    def resource(self, api: SirenApi, operation: SirenOperation) -> SirenResource | None:
        if operation.resource is None:
            return None
        matches = [
            resource for resource in api.resources if resource.reference == operation.resource]
        if len(matches) != 1:
            raise SirenityError(
                f"Siren operation references unknown resource: {operation.name}")
        return matches[0]

    def validate_result(self, response: SirenResponse, result: object) -> None:
        if response.shape == "empty" and result is not None:
            raise SirenityError(
                "OpenAPI content-free response requires a null result")
        if response.shape == "object" and not isinstance(result, Mapping):
            raise SirenityError(
                "OpenAPI object response requires a mapping result")
        if self.paginated(response):
            items = self.page_items(response)
            if (
                not isinstance(result, Mapping)
                or not isinstance(result.get(items), list)
                or any(not isinstance(item, Mapping) for item in result[items])
            ):
                raise SirenityError(
                    "OpenAPI paginated response requires a list of mapping items")
        if response.shape == "array" and (
            not isinstance(result, list) or any(
                not isinstance(item, Mapping) for item in result)
        ):
            raise SirenityError(
                "OpenAPI array response requires a list of mapping results")

    def entity(
        self, api: SirenApi, resource: SirenResource | None, context: SirenResponseContext, response: SirenResponse
    ) -> SirenDocument:
        if resource is None or not isinstance(context.result, Mapping):
            raise SirenityError(
                "Siren entity response requires an operation-owned resource")
        request = SirenContext(
            base_url=context.base_url,
            resource=resource.name,
            title=context.title,
            value=context.result,
            relationships=(*context.relationships, *
                           self.relationships(api, response, context.result)),
            path_values=context.path_values,
            query=context.query,
            capabilities=context.capabilities,
            action_bindings={binding.operation: binding.fields for binding in response.bindings},
        )
        return self.projection.project_resource(api, request, resource)

    def collection(
        self, api: SirenApi, resource: SirenResource | None, context: SirenResponseContext, response: SirenResponse
    ) -> SirenDocument:
        if resource is None or not isinstance(context.result, list):
            raise SirenityError(
                "Siren collection response requires an operation-owned resource")
        request = SirenContext(
            base_url=context.base_url,
            scope=SirenScope.COLLECTION,
            resource=resource.name,
            title=context.title,
            items=tuple(context.result),
            item_titles=context.item_titles,
            item_capabilities=context.item_capabilities,
            relationships=(*context.relationships, *
                           self.relationships(api, response, context.result)),
            path_values=context.path_values,
            query=context.query,
            capabilities=context.capabilities,
            action_bindings={binding.operation: binding.fields for binding in response.bindings},
        )
        return self.projection.project_resource(api, request, resource)

    def page(
        self,
        api: SirenApi,
        operation: SirenOperation,
        resource: SirenResource,
        context: SirenResponseContext,
        response: SirenResponse,
    ) -> SirenDocument:
        if not isinstance(context.result, Mapping) or not self.paginated(response):
            raise SirenityError(
                "Siren paginated response requires an operation-owned collection resource")
        items_name = self.page_items(response)
        items = context.result[items_name]
        if not isinstance(items, list):
            raise SirenityError("Siren paginated response items must be a list")
        properties = {name: value for name, value in context.result.items() if name != items_name}
        request = SirenContext(
            base_url=context.base_url,
            scope=SirenScope.COLLECTION,
            resource=resource.name,
            title=context.title,
            value=properties,
            items=tuple(items),
            item_titles=context.item_titles,
            item_capabilities=context.item_capabilities,
            relationships=(*context.relationships, *self.relationships(api, response, context.result)),
            path_values=context.path_values,
            query=context.query,
            capabilities=context.capabilities,
            action_bindings={binding.operation: binding.fields for binding in response.bindings},
        )
        document = self.projection.project_resource(api, request, resource)
        next_links = self.pagination_links(api, operation, resource, context, response)
        return document.model_copy(update={"links": (*(document.links or ()), *next_links)})

    def pagination_links(
        self,
        api: SirenApi,
        operation: SirenOperation,
        resource: SirenResource,
        context: SirenResponseContext,
        response: SirenResponse,
    ) -> tuple[SirenLink, ...]:
        if not isinstance(context.result, Mapping) or not self.paginated(response):
            raise SirenityError("Siren paginated response requires has_more metadata")
        has_more = context.result.get("has_more")
        if not isinstance(has_more, bool):
            raise SirenityError("Siren paginated response has_more value must be boolean")
        if not has_more:
            return ()
        links = [link for link in response.links if "next" in link.rel]
        if len(links) != 1:
            raise SirenityError("Siren paginated response requires exactly one next link")
        link = links[0]
        target = self.operation(api, link.operation)
        path_values = dict(context.path_values)
        query_names = set()
        query_values = []
        for name, expression in link.parameters.items():
            value = self.pointer(expression, context.result)
            if value is None:
                raise SirenityError("Siren pagination continuation values cannot be null")
            if name.startswith("path."):
                path_values[name[len("path."):]] = value
            elif name.startswith("query."):
                query_name = name[len("query."):]
                query_names.add(query_name)
                query_values.append((query_name, value))
            elif any(field.name == name for field in target.fields):
                query_names.add(name)
                query_values.append((name, value))
            else:
                path_values[name] = value
        query = tuple(
            (name, value) for name, value in context.query if name not in query_names
        ) + tuple(query_values)
        request = SirenContext(
            base_url=context.base_url,
            scope=SirenScope.COLLECTION,
            resource=resource.name,
            path_values=path_values,
            query=query,
        )
        return (SirenLink(
            rel=("next",),
            title="Next page",
            href=self.hrefs.href(target.route.path, request, resource),
        ),)

    def paginated(self, response: SirenResponse) -> bool:
        return any("next" in link.rel for link in response.links)

    def page_items(self, response: SirenResponse) -> str:
        if not isinstance(response.definition, Mapping):
            raise SirenityError("Siren paginated response requires an object schema")
        properties = response.definition.get("properties")
        if not isinstance(properties, Mapping):
            raise SirenityError("Siren paginated response requires object properties")
        candidates = [
            name
            for name, value in properties.items()
            if (
                isinstance(value, Mapping)
                and value.get("type") == "array"
                and isinstance(value.get("items"), Mapping)
                and value["items"].get("type") == "object"
            )
        ]
        if len(candidates) != 1:
            raise SirenityError("Siren paginated response requires exactly one item collection")
        return candidates[0]

    def command(
        self, api: SirenApi, operation: SirenOperation, resource: SirenResource | None,
        context: SirenResponseContext, response: SirenResponse
    ) -> SirenDocument:
        if not isinstance(context.result, Mapping):
            raise SirenityError(
                "Siren command response requires a mapping result")
        request = SirenContext(
            base_url=context.base_url,
            scope=SirenScope.ROOT,
            path_values=context.path_values,
            query=context.query,
        )
        links = [SirenLink(
            rel=("self",),
            title=context.title or operation.title,
            href=self.hrefs.href(operation.route.path,
                                 request, resource, context.result),
        )]
        for relationship in self.relationships(api, response, context.result):
            target = self.resource(
                api, self.operation(api, relationship.resource))
            if target is None:
                raise SirenityError(
                    "Siren response link target requires a resource")
            path = target.collection.path if relationship.scope == SirenScope.COLLECTION else target.entity.path
            if path is None:
                raise SirenityError(
                    f"Siren response link target has no entity route: {target.name}")
            links.append(SirenLink(
                rel=relationship.rel,
                title=target.title,
                href=self.hrefs.href(
                    path,
                    request.model_copy(
                        update={"path_values": relationship.path_values}),
                    target,
                ),
            ))
        return SirenDocument(
            class_=("command-result",),
            title=context.title or operation.title,
            properties=context.result,
            links=tuple(links),
        )

    def relationships(
        self, api: SirenApi, response: SirenResponse, result: object
    ) -> tuple[SirenRelationship, ...]:
        links = []
        for link in response.links:
            if "next" in link.rel:
                continue
            target = self.operation(api, link.operation)
            resource = self.resource(api, target)
            if resource is None:
                raise SirenityError(
                    "Siren response link target requires a resource")
            path = resource.collection.path if link.scope == SirenScope.COLLECTION else resource.entity.path
            if path is None:
                raise SirenityError(
                    f"Siren response link target has no entity route: {resource.name}")
            required = tuple(
                segment[1:-1]
                for segment in path.split("/")
                if segment.startswith("{") and segment.endswith("}")
            )
            values = {
                self.parameter_name(name): self.pointer(expression, result)
                for name, expression in link.parameters.items()
            }
            if set(values) != set(required):
                raise SirenityError(
                    "Siren response link parameters do not match the target route")
            links.append(SirenRelationship(
                rel=link.rel,
                resource=resource.name,
                scope=link.scope,
                path_values=values,
            ))
        return tuple(links)

    def parameter_name(self, name: str) -> str:
        if name.startswith("path."):
            return name[len("path."):]
        return name

    def pointer(self, expression: str, result: object) -> object:
        prefix = "$response.body#"
        if not expression.startswith(prefix):
            raise SirenityError(
                f"Siren response link runtime expression is unsupported: {expression}")
        pointer = expression[len(prefix):]
        if pointer == "":
            return result
        if not pointer.startswith("/"):
            raise SirenityError(
                f"Siren response link runtime expression is invalid: {expression}")
        value = result
        for token in pointer[1:].split("/"):
            token = token.replace("~1", "/").replace("~0", "~")
            if isinstance(value, Mapping) and token in value:
                value = value[token]
            elif isinstance(value, list) and token.isdecimal() and int(token) < len(value):
                value = value[int(token)]
            else:
                raise SirenityError(
                    f"Siren response link runtime expression is missing: {expression}")
        if isinstance(value, (dict, list)):
            raise SirenityError(
                f"Siren response link runtime expression is not scalar: {expression}")
        return value

    def empty(
        self, operation: SirenOperation, resource: SirenResource | None, context: SirenResponseContext
    ) -> SirenDocument:
        request = SirenContext(
            base_url=context.base_url,
            scope=SirenScope.ROOT,
            path_values=context.path_values,
            query=context.query,
        )
        return SirenDocument(
            class_=("empty",),
            title=context.title or operation.title,
            properties={"status": context.status},
            links=(SirenLink(
                rel=("self",),
                title=context.title or operation.title,
                href=self.hrefs.href(operation.route.path, request, resource),
            ),),
        )

    def error(
        self,
        operation: SirenOperation,
        resource: SirenResource | None,
        context: SirenResponseContext,
        request_url: str | None = None,
    ) -> SirenDocument:
        request = SirenContext(
            base_url=context.base_url,
            scope=SirenScope.ROOT,
            path_values=context.path_values,
            query=context.query,
        )
        properties = {"status": context.status}
        if isinstance(context.result, Mapping):
            properties = dict(context.result) | properties
        elif isinstance(context.result, list):
            properties["errors"] = context.result
        elif context.result is not None:
            properties["result"] = context.result
        return SirenDocument(
            class_=("error",),
            title=context.title or operation.title,
            properties=properties,
            links=(SirenLink(
                rel=("self",),
                title=context.title or operation.title,
                href=request_url or self.hrefs.href(
                    operation.route.path, request, resource),
            ),),
        )

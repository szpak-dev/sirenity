from collections.abc import Mapping
from dataclasses import dataclass

from pydantic import JsonValue, TypeAdapter, ValidationError
from wireup import injectable

from .... import graph
from ....graph.model import SirenContinuation, SirenContinuationKind, SirenSourceInputBinding
from ....shared import SirenHttpMethod, SirenityError, SirenRepresentation, SirenScope
from ... import SirenContext, SirenDocument, SirenHrefService, SirenLink, SirenRelationship, SirenResponseContext
from ..contracts.action import SirenActionDocumentService
from ..values.continuation import SirenProjectedContinuation
from ..values.follow_up import SirenProjectedFollowUp
from ..values.response import SirenProjectedResponse
from ..values.verification import SirenProjectedVerification
from .projection import SirenProjectionService


@injectable
@dataclass(frozen=True)
class SirenResponseProjectionService:
    projection: SirenProjectionService
    hrefs: SirenHrefService
    actions: SirenActionDocumentService

    def project(self, api: graph.SirenApi, context: SirenResponseContext) -> SirenDocument:
        return self.project_result(api, context).document

    def project_result(self, api: graph.SirenApi, context: SirenResponseContext) -> SirenProjectedResponse:
        operation = self.operation(api, context.operation_id)
        response = self.response(operation, context)
        resource = self.resource(api, operation)
        self.validate_result(response, context.result)
        if context.status >= 400:
            return SirenProjectedResponse(document=self.error(operation, resource, context, ""))
        if context.representation == SirenRepresentation.ROOT and response.shape != "object":
            raise SirenityError("Siren root response requires an OpenAPI object response")
        if response.shape == "empty":
            document = self.empty(operation, resource, context)
        elif response.shape == "array":
            if context.representation not in {None, SirenRepresentation.COLLECTION}:
                raise SirenityError("OpenAPI array response requires collection representation")
            document = self.collection(api, resource, context, response)
        elif self.paginated(response):
            if context.representation not in {None, SirenRepresentation.COLLECTION}:
                raise SirenityError("OpenAPI paginated response requires collection representation")
            if resource is None:
                raise SirenityError("OpenAPI paginated response requires a collection resource")
            document = self.page(api, resource, context, response)
        else:
            representation = context.representation
            if not representation and operation.scope == SirenScope.ROOT and operation.route == api.root.route:
                representation = SirenRepresentation.ROOT
            if representation == SirenRepresentation.ROOT:
                document = self.root(api, operation, context)
            elif (
                not representation
                and resource is not None
                and operation.route in {resource.collection, resource.entity}
            ):
                document = self.entity(api, resource, context, response)
            elif not representation or representation == SirenRepresentation.COMMAND:
                document = self.command(api, operation, resource, context, response)
            elif representation == SirenRepresentation.ENTITY:
                document = self.entity(api, resource, context, response)
            else:
                raise SirenityError("OpenAPI object response cannot use collection representation")
        continuations = self.project_continuations(api, context, response)
        follow_ups = self.project_follow_ups(api, context, operation, response)
        if continuations:
            compiled = response.continuations[0]
            target = self.operation(api, continuations[0].operation_id)
            if target.method == SirenHttpMethod.GET and not any(
                binding.target_location == "body" for binding in compiled.source_inputs
            ):
                title = "Next page" if self.paginated(response) else target.title
                document = document.model_copy(
                    update={
                        "links": (
                            *(document.links or ()),
                            SirenLink(rel=("next",), title=title, href=continuations[0].href),
                        )
                    }
                )
            else:
                path_values, query, arguments = self.continuation_arguments(context, compiled, target)
                target_resource = self.resource(api, target)
                action_bindings = {
                    field.name: f"$response.body#/{field.name.replace('~', '~0').replace('/', '~1')}"
                    for field in target.fields
                    if field.name in arguments
                }
                request = SirenContext(
                    base_url=context.base_url,
                    scope=target.scope,
                    resource=target_resource.name if target_resource is not None else "",
                    value=arguments,
                    path_values=path_values,
                    query=query,
                    action_bindings={target.name: action_bindings},
                )
                document = document.model_copy(
                    update={
                        "actions": (
                            *(document.actions or ()),
                            self.actions.action(target, request, target_resource, arguments),
                        )
                    }
                )
        for link in response.links:
            target = self.operation(api, link.operation)
            if not link.source_inputs:
                continue
            if not self.navigation_target_supported(
                context, target, link.source_inputs
            ) or not self.navigation_supported(context, link, target):
                continue
            path_values, query, arguments = self.navigation_arguments(context, link, target)
            projected = tuple(
                follow_up
                for follow_up in follow_ups
                if follow_up.operation_id == target.name and follow_up.arguments == arguments
            )
            if not projected:
                continue
            target_resource = self.resource(api, target)
            if target.method == SirenHttpMethod.GET and not any(
                binding.target_location == "body" for binding in link.source_inputs
            ):
                document = document.model_copy(
                    update={
                        "links": (
                            *(document.links or ()),
                            SirenLink(
                                rel=link.rel,
                                title=target_resource.title if target_resource is not None else target.title,
                                href=projected[0].href,
                            ),
                        )
                    }
                )
                continue
            action_bindings = {
                field.name: f"$response.body#/{field.name.replace('~', '~0').replace('/', '~1')}"
                for field in target.fields
                if field.name in arguments
            }
            request = SirenContext(
                base_url=context.base_url,
                scope=target.scope,
                resource=target_resource.name if target_resource is not None else "",
                value=arguments,
                path_values=path_values,
                query=query,
                action_bindings={target.name: action_bindings},
            )
            document = document.model_copy(
                update={
                    "actions": (
                        *(document.actions or ()),
                        self.actions.action(target, request, target_resource, arguments),
                    )
                }
            )
        return SirenProjectedResponse(
            document=document,
            continuations=continuations,
            verifications=self.project_verifications(api, context, operation, response),
            follow_ups=follow_ups,
        )

    def root(
        self, api: graph.SirenApi, operation: graph.SirenOperation, context: SirenResponseContext
    ) -> SirenDocument:
        if operation.scope != SirenScope.ROOT:
            raise SirenityError("Siren root response requires a root operation and mapping result")
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

    def operation(self, api: graph.SirenApi, operation_id: str) -> graph.SirenOperation:
        matches = [operation for operation in api.operations if operation.name == operation_id]
        if len(matches) != 1:
            raise SirenityError(f"Siren response references unknown operation: {operation_id}")
        return matches[0]

    def response(self, operation: graph.SirenOperation, context: SirenResponseContext) -> graph.SirenResponse:
        candidates = list(self.candidates(operation, context))
        if not context.media_type and len(candidates) > 1:
            json_candidates = [response for response in candidates if response.media_type == "application/json"]
            candidates = json_candidates if len(json_candidates) == 1 else candidates
        if len(candidates) != 1:
            raise SirenityError(
                f"Siren response requires exactly one status and media type match: {operation.name} {context.status}"
            )
        return candidates[0]

    def has_response(self, api: graph.SirenApi, context: SirenResponseContext) -> bool:
        operation = self.operation(api, context.operation_id)
        return bool(self.candidates(operation, context))

    def candidates(
        self, operation: graph.SirenOperation, context: SirenResponseContext
    ) -> tuple[graph.SirenResponse, ...]:
        exact = [response for response in operation.responses if response.status == str(context.status)]
        ranged = [
            response
            for response in operation.responses
            if len(response.status) == 3
            and response.status[0] == str(context.status)[0]
            and response.status[1:].upper() == "XX"
        ]
        defaults = [response for response in operation.responses if response.status == "default"]
        candidates = exact or ranged or defaults
        if context.media_type:
            candidates = [response for response in candidates if response.media_type == context.media_type]
        return tuple(candidates)

    def project_error(
        self, api: graph.SirenApi, context: SirenResponseContext, request_url: str
    ) -> SirenDocument:
        operation = self.operation(api, context.operation_id)
        resource = self.resource(api, operation)
        return self.error(operation, resource, context, request_url)

    def resource(self, api: graph.SirenApi, operation: graph.SirenOperation) -> graph.SirenResource | None:
        if not operation.resource:
            return None
        matches = [resource for resource in api.resources if resource.reference == operation.resource]
        if len(matches) != 1:
            raise SirenityError(f"Siren operation references unknown resource: {operation.name}")
        return matches[0]

    def validate_result(self, response: graph.SirenResponse, result: JsonValue) -> None:
        if response.shape == "empty" and result is not None:
            raise SirenityError("OpenAPI content-free response requires a null result")
        try:
            if response.shape == "array":
                TypeAdapter(list[JsonValue]).validate_python(result)
            elif response.shape == "object":
                TypeAdapter(dict[str, JsonValue]).validate_python(result)
        except ValidationError as error:
            shape = "array" if response.shape == "array" else "mapping"
            raise SirenityError(f"OpenAPI {response.shape} response requires a {shape} result") from error

    def entity(
        self,
        api: graph.SirenApi,
        resource: graph.SirenResource | None,
        context: SirenResponseContext,
        response: graph.SirenResponse,
    ) -> SirenDocument:
        if resource is None:
            raise SirenityError("Siren entity response requires an operation-owned resource")
        request = SirenContext(
            base_url=context.base_url,
            resource=resource.name,
            title=context.title,
            value=context.result,
            relationships=(*context.relationships, *self.relationships(api, response, context.result)),
            path_values=context.path_values,
            query=context.query,
            capabilities=context.capabilities,
            action_bindings={binding.operation: binding.fields for binding in response.bindings},
        )
        return self.projection.project_resource(api, request, resource)

    def collection(
        self,
        api: graph.SirenApi,
        resource: graph.SirenResource | None,
        context: SirenResponseContext,
        response: graph.SirenResponse,
    ) -> SirenDocument:
        if resource is None:
            raise SirenityError("Siren collection response requires an operation-owned resource")
        request = SirenContext(
            base_url=context.base_url,
            scope=SirenScope.COLLECTION,
            resource=resource.name,
            title=context.title,
            items=tuple(context.result),
            item_titles=context.item_titles,
            item_capabilities=context.item_capabilities,
            relationships=(*context.relationships, *self.relationships(api, response, context.result)),
            path_values=context.path_values,
            query=context.query,
            capabilities=context.capabilities,
            action_bindings={binding.operation: binding.fields for binding in response.bindings},
        )
        return self.projection.project_resource(api, request, resource)

    def page(
        self,
        api: graph.SirenApi,
        resource: graph.SirenResource,
        context: SirenResponseContext,
        response: graph.SirenResponse,
    ) -> SirenDocument:
        if not self.paginated(response):
            raise SirenityError("Siren paginated response requires an operation-owned collection resource")
        items_name = self.page_items(response)
        items = context.result[items_name]
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
        return self.projection.project_resource(api, request, resource)

    def project_continuations(
        self,
        api: graph.SirenApi,
        context: SirenResponseContext,
        response: graph.SirenResponse,
    ) -> tuple[SirenProjectedContinuation, ...]:
        if not response.continuations:
            return ()
        if len(response.continuations) != 1:
            raise SirenityError("Siren response requires one compiled continuation")
        has_more = context.result["has_more"]
        match has_more:
            case False:
                return ()
            case True:
                pass
            case _:
                raise SirenityError("Siren continuation has_more value must be boolean")
        continuation = response.continuations[0]
        target = self.operation(api, continuation.operation)
        if continuation.source_inputs and target.name not in context.navigation_capabilities:
            return ()
        target_resource = self.resource(api, target)
        path_values, query, arguments = self.continuation_arguments(context, continuation, target)
        request = SirenContext(
            base_url=context.base_url,
            scope=target.scope,
            resource=target_resource.name if target_resource is not None else "",
            path_values=path_values,
            query=query,
        )
        return (
            SirenProjectedContinuation(
                operation_id=target.name,
                arguments=arguments,
                href=self.hrefs.href(target.route.path, request, target_resource or "", {}, True),
            ),
        )

    def continuation_arguments(
        self,
        context: SirenResponseContext,
        continuation: SirenContinuation,
        target: graph.SirenOperation,
    ) -> tuple[
        dict[str, JsonValue],
        tuple[tuple[str, JsonValue], ...],
        dict[str, JsonValue],
    ]:
        target_path = {
            segment[1:-1]
            for segment in target.route.path.split("/")
            if segment.startswith("{") and segment.endswith("}")
        }
        target_parameters = target.input.parameters
        target_query = {parameter.name for parameter in target_parameters if parameter.location == "query"}
        required_query = {
            parameter.name for parameter in target_parameters if parameter.location == "query" and parameter.required
        }
        path_values = (
            {}
            if continuation.source_inputs
            else {name: value for name, value in context.path_values.items() if name in target_path}
        )
        replaced_query = {parameter.name for parameter in continuation.parameters if parameter.location == "query"}
        query_values = (
            []
            if continuation.source_inputs
            else [(name, value) for name, value in context.query if name in target_query and name not in replaced_query]
        )
        body_values: dict[str, JsonValue] = {}
        source_query = dict(context.query)
        for binding in continuation.source_inputs:
            value = (
                context.path_values[binding.source_name]
                if binding.source_location == "path"
                else source_query[binding.source_name]
                if binding.source_location == "query"
                else context.body[binding.source_name]
            )
            if binding.target_location == "path":
                path_values[binding.target_name] = value
            elif binding.target_location == "query":
                query_values.append((binding.target_name, value))
            else:
                body_values[binding.target_name] = value
        for parameter in continuation.parameters:
            value = self.continuation_value(parameter.pointer, context.result)
            if value is None:
                raise SirenityError("Siren continuation values cannot be null")
            if parameter.location == "path":
                path_values[parameter.name] = value
            else:
                query_values.append((parameter.name, value))
        query = tuple(query_values)
        missing_path = target_path - path_values.keys()
        missing_query = required_query - {name for name, _ in query}
        if missing_path or missing_query:
            raise SirenityError("Siren continuation is missing required target arguments")
        arguments = dict(path_values)
        arguments.update(query)
        arguments.update(body_values)
        return path_values, query, arguments

    def continuation_value(self, pointer: tuple[str, ...], result: Mapping[str, JsonValue]) -> JsonValue:
        value: JsonValue = dict(result)
        for token in pointer:
            value = value[token]
        return value

    def project_verifications(
        self,
        api: graph.SirenApi,
        context: SirenResponseContext,
        source: graph.SirenOperation,
        response: graph.SirenResponse,
    ) -> tuple[SirenProjectedVerification, ...]:
        if source.method not in {
            SirenHttpMethod.DELETE,
            SirenHttpMethod.PATCH,
            SirenHttpMethod.POST,
            SirenHttpMethod.PUT,
        }:
            return ()
        verifications: list[SirenProjectedVerification] = []
        for link in response.links:
            if link.source_inputs:
                continue
            target = self.operation(api, link.operation)
            if (
                target.method != SirenHttpMethod.GET
                or not self.navigation_target_supported(context, target, link.source_inputs)
                or not self.navigation_supported(context, link, target)
            ):
                continue
            path_values, query, arguments = self.navigation_arguments(context, link, target)
            resource = self.resource(api, target)
            request = SirenContext(
                base_url=context.base_url,
                scope=target.scope,
                resource=resource.name if resource is not None else "",
                path_values=path_values,
                query=query,
            )
            verification = SirenProjectedVerification(
                operation_id=target.name,
                arguments=arguments,
                href=self.hrefs.href(target.route.path, request, resource or "", {}, True),
            )
            if verification not in verifications:
                verifications.append(verification)
        for target, resource in self.canonical_verification_targets(api, context, source, response):
            path_values = self.canonical_verification_path_values(context, resource, target)
            query = self.verification_query(context, target)
            arguments = dict(path_values)
            arguments.update(query)
            request = SirenContext(
                base_url=context.base_url,
                scope=target.scope,
                resource=resource.name,
                path_values=path_values,
                query=query,
            )
            verification = SirenProjectedVerification(
                operation_id=target.name,
                arguments=arguments,
                href=self.hrefs.href(target.route.path, request, resource, {}, True),
            )
            if verification not in verifications:
                verifications.append(verification)
        return tuple(verifications)

    def project_follow_ups(
        self,
        api: graph.SirenApi,
        context: SirenResponseContext,
        source: graph.SirenOperation,
        response: graph.SirenResponse,
    ) -> tuple[SirenProjectedFollowUp, ...]:
        if not 200 <= context.status < 300:
            return ()
        follow_ups: list[SirenProjectedFollowUp] = []
        for link in response.links:
            if source.method != SirenHttpMethod.GET and not link.source_inputs:
                continue
            target = self.operation(api, link.operation)
            if (
                (target.method != SirenHttpMethod.GET and not link.source_inputs)
                or not self.navigation_target_supported(context, target, link.source_inputs)
                or not self.navigation_supported(context, link, target)
            ):
                continue
            path_values, query, arguments = self.navigation_arguments(context, link, target)
            resource = self.resource(api, target)
            request = SirenContext(
                base_url=context.base_url,
                scope=target.scope,
                resource=resource.name if resource is not None else "",
                path_values=path_values,
                query=query,
            )
            follow_up = SirenProjectedFollowUp(
                operation_id=target.name,
                arguments=arguments,
                href=self.hrefs.href(target.route.path, request, resource or "", {}, True),
            )
            if follow_up not in follow_ups:
                follow_ups.append(follow_up)
        return tuple(follow_ups)

    def canonical_verification_targets(
        self,
        api: graph.SirenApi,
        context: SirenResponseContext,
        source: graph.SirenOperation,
        response: graph.SirenResponse,
    ) -> tuple[tuple[graph.SirenOperation, graph.SirenResource], ...]:
        if source.method not in {SirenHttpMethod.PATCH, SirenHttpMethod.POST, SirenHttpMethod.PUT}:
            return ()
        if response.shape != "object" or not source.resource:
            return ()
        resource = self.resource(api, source)
        if resource is None or not resource.entity.path:
            return ()
        if source.route not in {resource.collection, resource.entity}:
            return ()
        targets = tuple(
            operation
            for operation in api.operations
            if operation.resource == resource.reference
            and operation.method == SirenHttpMethod.GET
            and operation.scope == SirenScope.ENTITY
            and operation.route == resource.entity
        )
        if len(targets) != 1:
            return ()
        target = targets[0]
        if not self.navigation_target_supported(context, target, ()):
            return ()
        path_values = self.canonical_verification_path_values(context, resource, target)
        target_path = self.operation_path_parameters(target)
        required_query = self.required_query_parameters(target)
        available_query = {name for name, _ in self.verification_query(context, target)}
        if target_path - path_values.keys() or required_query - available_query:
            return ()
        return ((target, resource),)

    def canonical_verification_path_values(
        self,
        context: SirenResponseContext,
        resource: graph.SirenResource,
        target: graph.SirenOperation,
    ) -> dict[str, JsonValue]:
        target_path = self.operation_path_parameters(target)
        path_values = {
            name: value for name, value in context.path_values.items() if name in target_path and value is not None
        }
        result = context.result if isinstance(context.result, dict) else {}
        for name in target_path - path_values.keys():
            values = tuple(
                result[candidate]
                for candidate in resource.path_bindings[name]
                if candidate in result and result[candidate] is not None
            )
            if values:
                path_values[name] = values[0]
        return path_values

    def navigation_target_supported(
        self,
        context: SirenResponseContext,
        target: graph.SirenOperation,
        source_inputs: tuple[SirenSourceInputBinding, ...],
    ) -> bool:
        if target.name not in context.navigation_capabilities:
            return False
        target_parameters = target.input.parameters
        if any(parameter.required and parameter.location in {"header", "cookie"} for parameter in target_parameters):
            return False
        if (
            not source_inputs
            and target.input.present
            and any(delegated.required for delegated in target.input.delegated_inputs)
        ):
            return False
        return bool(source_inputs) or not target.input.present or not target.input.definition.get("required")

    def navigation_supported(
        self,
        context: SirenResponseContext,
        link: graph.SirenResponseLink,
        target: graph.SirenOperation,
    ) -> bool:
        target_path = self.operation_path_parameters(target)
        target_parameters = target.input.parameters
        target_query = {parameter.name for parameter in target_parameters if parameter.location == "query"}
        required_query = self.required_query_parameters(target)
        if any(self.pointer(expression, context.result) is None for expression in link.parameters.values()):
            return False
        linked = {self.parameter_name(name) for name in link.parameters}
        bound_path = {binding.target_name for binding in link.source_inputs if binding.target_location == "path"}
        bound_query = {binding.target_name for binding in link.source_inputs if binding.target_location == "query"}
        available_path = target_path.intersection(linked) | bound_path
        available_query = target_query.intersection(linked) | bound_query
        if not link.source_inputs:
            available_path.update(
                name for name, value in context.path_values.items() if name in target_path and value is not None
            )
            available_query.update(target_query.intersection(name for name, _ in context.query))
        return target_path <= available_path and required_query <= available_query

    def navigation_arguments(
        self,
        context: SirenResponseContext,
        link: graph.SirenResponseLink,
        target: graph.SirenOperation,
    ) -> tuple[
        dict[str, JsonValue],
        tuple[tuple[str, JsonValue], ...],
        dict[str, JsonValue],
    ]:
        target_path = {
            segment[1:-1]
            for segment in target.route.path.split("/")
            if segment.startswith("{") and segment.endswith("}")
        }
        target_parameters = target.input.parameters
        target_query = {parameter.name for parameter in target_parameters if parameter.location == "query"}
        path_values = (
            {}
            if link.source_inputs
            else {name: value for name, value in context.path_values.items() if name in target_path}
        )
        mapped_query = {
            self.parameter_name(name)
            for name in link.parameters
            if name.startswith("query.") or self.parameter_name(name) in target_query
        }
        query_values = (
            []
            if link.source_inputs
            else [(name, value) for name, value in context.query if name in target_query and name not in mapped_query]
        )
        body_values: dict[str, JsonValue] = {}
        source_query = dict(context.query)
        for binding in link.source_inputs:
            value = (
                context.path_values[binding.source_name]
                if binding.source_location == "path"
                else source_query[binding.source_name]
                if binding.source_location == "query"
                else context.body[binding.source_name]
            )
            if binding.target_location == "path":
                path_values[binding.target_name] = value
            elif binding.target_location == "query":
                query_values.append((binding.target_name, value))
            else:
                body_values[binding.target_name] = value
        for name, expression in link.parameters.items():
            argument = self.parameter_name(name)
            value = self.pointer(expression, context.result)
            if value is None:
                raise SirenityError("Siren navigation values cannot be null")
            if name.startswith("path.") or argument in target_path:
                path_values[argument] = value
            else:
                query_values.append((argument, value))
        query = tuple(query_values)
        arguments = dict(path_values)
        arguments.update(query)
        arguments.update(body_values)
        return path_values, query, arguments

    def operation_path_parameters(self, operation: graph.SirenOperation) -> set[str]:
        return {
            segment[1:-1]
            for segment in operation.route.path.split("/")
            if segment.startswith("{") and segment.endswith("}")
        }

    def required_query_parameters(self, operation: graph.SirenOperation) -> set[str]:
        parameters = operation.input.parameters
        return {parameter.name for parameter in parameters if parameter.location == "query" and parameter.required}

    def verification_query(
        self,
        context: SirenResponseContext,
        target: graph.SirenOperation,
    ) -> tuple[tuple[str, JsonValue], ...]:
        parameters = target.input.parameters
        target_query = {parameter.name for parameter in parameters if parameter.location == "query"}
        return tuple((name, value) for name, value in context.query if name in target_query)

    def paginated(self, response: graph.SirenResponse) -> bool:
        return any(continuation.kind == SirenContinuationKind.PAGINATION for continuation in response.continuations)

    def page_items(self, response: graph.SirenResponse) -> str:
        properties = response.definition["properties"]
        candidates = [
            name
            for name, value in properties.items()
            if (value.get("type") == "array" and value["items"].get("type") == "object")
        ]
        if len(candidates) != 1:
            raise SirenityError("Siren paginated response requires exactly one item collection")
        return candidates[0]

    def command(
        self,
        api: graph.SirenApi,
        operation: graph.SirenOperation,
        resource: graph.SirenResource | None,
        context: SirenResponseContext,
        response: graph.SirenResponse,
    ) -> SirenDocument:
        request = SirenContext(
            base_url=context.base_url,
            scope=SirenScope.ROOT,
            path_values=context.path_values,
            query=context.query,
        )
        links = [
            SirenLink(
                rel=("self",),
                title=context.title or operation.title,
                href=self.hrefs.href(operation.route.path, request, resource or "", context.result, True),
            )
        ]
        for link in response.links:
            if "next" in link.rel:
                continue
            if link.source_inputs:
                continue
            target_operation = self.operation(api, link.operation)
            target = self.resource(api, target_operation)
            if target is None:
                raise SirenityError("Siren response link target requires a resource")
            path = target.collection.path if link.scope == SirenScope.COLLECTION else target.entity.path
            if path is None:
                raise SirenityError(f"Siren response link target has no entity route: {target.name}")
            required = tuple(
                segment[1:-1] for segment in path.split("/") if segment.startswith("{") and segment.endswith("}")
            )
            values = {
                self.parameter_name(name): self.pointer(expression, context.result)
                for name, expression in link.parameters.items()
                if name.startswith("path.") or self.parameter_name(name) in required
            }
            if set(values) != set(required):
                raise SirenityError("Siren response link parameters do not match the target route")
            links.append(
                SirenLink(
                    rel=link.rel,
                    title=target.title,
                    href=self.hrefs.href(
                        path,
                        request.model_copy(update={"path_values": values}),
                        target,
                        {},
                        True,
                    ),
                )
            )
        return SirenDocument(
            class_=("command-result",),
            title=context.title or operation.title,
            properties=context.result,
            links=tuple(links),
        )

    def relationships(
        self, api: graph.SirenApi, response: graph.SirenResponse, result: JsonValue
    ) -> tuple[SirenRelationship, ...]:
        links = []
        for link in response.links:
            if "next" in link.rel:
                continue
            if link.source_inputs:
                continue
            target = self.operation(api, link.operation)
            resource = self.resource(api, target)
            if resource is None:
                raise SirenityError("Siren response link target requires a resource")
            path = resource.collection.path if link.scope == SirenScope.COLLECTION else resource.entity.path
            if path is None:
                raise SirenityError(f"Siren response link target has no entity route: {resource.name}")
            required = tuple(
                segment[1:-1] for segment in path.split("/") if segment.startswith("{") and segment.endswith("}")
            )
            values = {
                self.parameter_name(name): self.pointer(expression, result)
                for name, expression in link.parameters.items()
                if name.startswith("path.") or self.parameter_name(name) in required
            }
            if set(values) != set(required):
                raise SirenityError("Siren response link parameters do not match the target route")
            links.append(
                SirenRelationship(
                    rel=link.rel,
                    resource=resource.name,
                    scope=link.scope,
                    path_values=values,
                )
            )
        return tuple(links)

    def parameter_name(self, name: str) -> str:
        for prefix in ("path.", "query."):
            if name.startswith(prefix):
                return name[len(prefix) :]
        return name

    def pointer(self, expression: str, result: JsonValue) -> JsonValue:
        prefix = "$response.body#"
        if not expression.startswith(prefix):
            raise SirenityError(f"Siren response link runtime expression is unsupported: {expression}")
        pointer = expression[len(prefix) :]
        if pointer == "":
            return result
        if not pointer.startswith("/"):
            raise SirenityError(f"Siren response link runtime expression is invalid: {expression}")
        value = result
        for token in pointer[1:].split("/"):
            token = token.replace("~1", "/").replace("~0", "~")
            value = value[token]
        return value

    def empty(
        self,
        operation: graph.SirenOperation,
        resource: graph.SirenResource | None,
        context: SirenResponseContext,
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
            links=(
                SirenLink(
                    rel=("self",),
                    title=context.title or operation.title,
                    href=self.hrefs.href(operation.route.path, request, resource or "", {}, True),
                ),
            ),
        )

    def error(
        self,
        operation: graph.SirenOperation,
        resource: graph.SirenResource | None,
        context: SirenResponseContext,
        request_url: str,
    ) -> SirenDocument:
        request = SirenContext(
            base_url=context.base_url,
            scope=SirenScope.ROOT,
            path_values=context.path_values,
            query=context.query,
        )
        properties = {"status": context.status}
        match context.result:
            case dict() as result:
                properties = result | properties
            case list() as result:
                properties["errors"] = result
            case result if result is not None:
                properties["result"] = result
        return SirenDocument(
            class_=("error",),
            title=context.title or operation.title,
            properties=properties,
            links=(
                SirenLink(
                    rel=("self",),
                    title=context.title or operation.title,
                    href=request_url or self.hrefs.href(operation.route.path, request, resource or "", {}, True),
                ),
            ),
        )

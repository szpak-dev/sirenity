import jsonschema
import pydantic
from jsonschema import Draft202012Validator

from ...graph import SirenInput
from ...shared import BaseState, SirenityError
from ..adapter import (
    SirenAdapter,
    SirenAdapterPolicy,
    SirenAdapterRequest,
    SirenCapabilityPolicy,
)
from .contracts.executor import SirenMcpExecutor
from .values.catalogue import SirenMcpToolCatalogue
from .values.execution import SirenMcpExecution
from .values.invocation import SirenMcpInvocation
from .values.operation import SirenMcpOperation
from .values.result import SirenMcpResult
from .values.tool import SirenMcpTool


class SirenMcpBridge(BaseState):
    adapter: SirenAdapter
    policy: SirenCapabilityPolicy
    executor: SirenMcpExecutor
    catalogue: SirenMcpToolCatalogue

    def tools(self) -> tuple[SirenMcpTool, ...]:
        return self.catalogue.snapshot()

    @property
    def catalogue_fingerprint(self) -> str:
        return self.catalogue.fingerprint

    def operation(self, invocation: SirenMcpInvocation) -> SirenMcpOperation:
        operations = [
            operation for operation in self.adapter.engine.api.operations if operation.name == invocation.operation_id
        ]
        if len(operations) != 1:
            raise SirenityError(f"Siren MCP invocation references unknown operation: {invocation.operation_id}")
        operation = operations[0]
        arguments = dict(invocation.arguments)
        input = self.adapter.engine.operation_input(operation.name) or SirenInput()
        parameters = input.parameters
        path_values = {
            parameter.name: arguments[parameter.name]
            for parameter in parameters
            if parameter.location == "path" and parameter.name in arguments
        }
        body_properties = input.definition.get("properties", {})
        body_required = input.definition.get("required", ())
        body_names = set(body_properties)
        query_values = {
            parameter.name: arguments[parameter.name]
            for parameter in parameters
            if parameter.location == "query" and parameter.name in arguments
        }
        body_values = {name: arguments[name] for name in body_names if name in arguments}
        header_values = {
            parameter.name: arguments[parameter.name]
            for parameter in parameters
            if parameter.location == "header" and parameter.name in arguments
        }
        cookie_values = {
            parameter.name: arguments[parameter.name]
            for parameter in parameters
            if parameter.location == "cookie" and parameter.name in arguments
        }
        for delegated in input.delegated_inputs:
            if delegated.name not in arguments:
                continue
            if delegated.location == "body":
                if delegated.name == "body":
                    body_values = {"body": arguments[delegated.name]}
                else:
                    body_values[delegated.name] = arguments[delegated.name]
        allowed = {parameter.name for parameter in parameters} | body_names
        allowed.update(item.name for item in input.delegated_inputs if item.location == "body")
        unknown = sorted(set(arguments) - allowed)
        if unknown:
            raise SirenityError(f"Siren MCP invocation has unknown arguments for {operation.name}: {unknown}")
        required = {parameter.name for parameter in parameters if parameter.required} | set(body_required)
        required.update(item.name for item in input.delegated_inputs if item.location == "body" and item.required)
        missing = sorted(name for name in required if name not in arguments)
        if missing:
            raise SirenityError(f"Siren MCP invocation is missing required arguments for {operation.name}: {missing}")
        tool = self.catalogue.tool(operation.name)
        Draft202012Validator(dict(tool.input_schema)).validate(arguments)
        for name, schema in body_properties.items():
            if name not in arguments:
                continue
            Draft202012Validator(schema).validate(arguments[name])
        for delegated in input.delegated_inputs:
            if delegated.name not in arguments:
                continue
            Draft202012Validator(dict(delegated.definition)).validate(arguments[delegated.name])
        body = None
        if body_values:
            body = body_values.get("body") if set(body_values) == {"body"} else body_values
        return SirenMcpOperation(
            operation_id=operation.name,
            method=operation.method,
            dispatch_path=self.adapter.render_path(operation.source_path, path_values),
            path_values=path_values,
            body=body,
            query_values=query_values,
            header_values=header_values,
            cookie_values=cookie_values,
        )

    def respond(self, request: SirenAdapterRequest) -> SirenMcpResult:
        response = self.adapter.respond(request)
        return SirenMcpResult(
            structured_content=response.payload,
            is_error=not 200 <= response.status < 300,
            continuations=tuple(
                SirenMcpInvocation(
                    operation_id=continuation.operation_id,
                    arguments=continuation.arguments,
                )
                for continuation in response.continuations
            ),
            verifications=tuple(
                SirenMcpInvocation(
                    operation_id=verification.operation_id,
                    arguments=verification.arguments,
                )
                for verification in response.verifications
            ),
        )

    def invoke(self, invocation: SirenMcpInvocation) -> SirenMcpResult:
        try:
            operation = self.operation(invocation)
        except (SirenityError, jsonschema.ValidationError, pydantic.ValidationError):
            return SirenMcpResult(
                structured_content={"detail": "Siren MCP invocation is invalid"},
                is_error=True,
            )
        request = self.executor.execute(operation)
        try:
            policy = self._policy(operation.operation_id, request)
            return self.respond(
                SirenAdapterRequest(
                    operation_id=operation.operation_id,
                    status=request.status,
                    result=request.result,
                    base_url=request.base_url,
                    request_url=request.request_url,
                    path_values=operation.path_values,
                    query=tuple(operation.query_values.items()),
                    headers=request.headers,
                    policy=policy,
                )
            )
        except SirenityError as error:
            return SirenMcpResult(
                structured_content={"detail": str(error)},
                is_error=True,
            )
        except (jsonschema.ValidationError, pydantic.ValidationError):
            return SirenMcpResult(
                structured_content={"detail": "Siren MCP invocation is invalid"},
                is_error=True,
            )

    def _policy(self, operation_id: str, request: SirenMcpExecution) -> SirenAdapterPolicy:
        return self.policy.select(operation_id, request.status, request, request.result)

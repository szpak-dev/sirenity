from collections.abc import Callable

from jsonschema import Draft202012Validator, ValidationError

from sirenity.contexts.runtime.adapter import (
    SirenAdapter,
    SirenAdapterPolicy,
    SirenAdapterRequest,
    SirenCapabilityPolicy,
)
from sirenity.contexts.shared import BaseState, SirenContractError, SirenityError

from ..contracts import SirenMcpExecutor
from ..values import SirenMcpExecution, SirenMcpInvocation, SirenMcpOperation, SirenMcpResult, SirenMcpTool


class SirenMcpBridge(BaseState):
    adapter: SirenAdapter
    policy: SirenCapabilityPolicy | Callable[..., object]
    executor: SirenMcpExecutor

    def tools(self) -> tuple[SirenMcpTool, ...]:
        values = []
        for operation in self.adapter.engine.api.operations:
            input = self.adapter.engine.operation_input(operation.name)
            properties = {}
            required = []
            definition = input.definition if input is not None else None
            body_properties = (
                definition.get("properties", {})
                if isinstance(definition, dict)
                else {}
            )
            body_required = (
                definition.get("required", ())
                if isinstance(definition, dict)
                else ()
            )
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
                schema["required"] = list(dict.fromkeys(required))
            values.append(SirenMcpTool(
                name=operation.name,
                title=operation.title,
                description=operation.description,
                input_schema=schema,
            ))
        return tuple(values)

    def operation(self, invocation: SirenMcpInvocation) -> SirenMcpOperation:
        operations = [
            operation
            for operation in self.adapter.engine.api.operations
            if operation.name == invocation.operation_id
        ]
        if len(operations) != 1:
            raise SirenityError(
                f"Siren MCP invocation references unknown operation: {invocation.operation_id}")
        operation = operations[0]
        arguments = dict(invocation.arguments)
        input = self.adapter.engine.operation_input(operation.name)
        parameters = input.parameters if input is not None else ()
        path_values = {
            parameter.name: arguments[parameter.name]
            for parameter in parameters
            if parameter.location == "path" and parameter.name in arguments
        }
        definition = input.definition if input is not None else None
        body_properties = (
            definition.get("properties", {})
            if isinstance(definition, dict)
            else {}
        )
        body_required = (
            definition.get("required", ())
            if isinstance(definition, dict)
            else ()
        )
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
        if input is not None:
            for delegated in input.delegated_inputs:
                if delegated.name not in arguments:
                    continue
                if delegated.location == "body":
                    if delegated.name == "body":
                        body_values = {"body": arguments[delegated.name]}
                    else:
                        body_values[delegated.name] = arguments[delegated.name]
        allowed = {parameter.name for parameter in parameters} | body_names
        if input is not None:
            allowed.update(
                item.name for item in input.delegated_inputs if item.location == "body")
        unknown = sorted(set(arguments) - allowed)
        if unknown:
            raise SirenityError(
                f"Siren MCP invocation has unknown arguments for {operation.name}: {unknown}")
        required = {parameter.name for parameter in parameters if parameter.required} | set(body_required)
        if input is not None:
            required.update(
                item.name for item in input.delegated_inputs
                if item.location == "body" and item.required
            )
        missing = sorted(name for name in required if name not in arguments)
        if missing:
            raise SirenityError(
                f"Siren MCP invocation is missing required arguments for {operation.name}: {missing}")
        tool = next(
            tool for tool in self.tools() if tool.name == operation.name)
        try:
            Draft202012Validator(dict(tool.input_schema)).validate(arguments)
        except ValidationError as error:
            raise SirenityError(
                f"Siren MCP invocation has invalid arguments for {operation.name}") from error
        for name, schema in body_properties.items():
            if name not in arguments or not isinstance(schema, dict):
                continue
            try:
                Draft202012Validator(schema).validate(arguments[name])
            except ValidationError as error:
                raise SirenityError(
                    f"Siren MCP invocation has invalid argument {name} for {operation.name}") from error
        if input is not None:
            for delegated in input.delegated_inputs:
                if delegated.name not in arguments:
                    continue
                try:
                    Draft202012Validator(dict(delegated.definition)).validate(
                        arguments[delegated.name])
                except ValidationError as error:
                    raise SirenityError(
                        f"Siren MCP invocation has invalid argument {delegated.name} for {operation.name}") from error
        body = None
        if body_values:
            body = body_values.get("body") if set(body_values) == {"body"} else body_values
        return SirenMcpOperation(
            operation_id=operation.name,
            path_values=path_values,
            body=body,
            query_values=query_values,
            header_values=header_values,
            cookie_values=cookie_values,
        )

    def respond(self, request: SirenAdapterRequest) -> SirenMcpResult:
        try:
            response = self.adapter.respond(request)
            return SirenMcpResult(structured_content=response.payload)
        except SirenContractError as error:
            return SirenMcpResult(
                structured_content={"location": error.location, "category": error.category, "detail": error.detail},
                is_error=True,
            )
        except SirenityError as error:
            return SirenMcpResult(structured_content={"detail": str(error)}, is_error=True)

    def invoke(self, invocation: SirenMcpInvocation) -> SirenMcpResult:
        """Normalize, execute once, and project one MCP tool invocation."""

        try:
            operation = self.operation(invocation)
        except SirenityError:
            return SirenMcpResult(
                structured_content={"detail": "Siren MCP invocation is invalid"},
                is_error=True,
            )
        try:
            request = self.executor.execute(operation)
        except Exception:
            return SirenMcpResult(
                structured_content={"detail": "Siren MCP executor failed"}, is_error=True)
        if not isinstance(request, SirenMcpExecution):
            return SirenMcpResult(
                structured_content={"detail": "Siren MCP executor must return SirenMcpExecution"},
                is_error=True,
            )
        policy = self._policy(operation.operation_id, request)
        if isinstance(policy, SirenMcpResult):
            return policy
        return self.respond(SirenAdapterRequest(
            operation_id=operation.operation_id,
            status=request.status,
            result=request.result,
            base_url=request.base_url,
            request_url=request.request_url,
            path_values=operation.path_values,
            query=tuple(operation.query_values.items()),
            headers=request.headers,
            policy=policy,
        ))

    def _policy(
        self, operation_id: str, request: SirenMcpExecution
    ) -> SirenAdapterPolicy | SirenMcpResult:
        try:
            selected = (
                self.policy.select(operation_id, request.status, request, request.result)
                if isinstance(self.policy, SirenCapabilityPolicy)
                else self.policy(operation_id, request.status, request, request.result)
            )
            if not isinstance(selected, SirenAdapterPolicy):
                raise SirenityError("Siren capability policy must return SirenAdapterPolicy")
            return selected
        except Exception:
            return SirenMcpResult(
                structured_content={"detail": "Siren capability policy failed"}, is_error=True)

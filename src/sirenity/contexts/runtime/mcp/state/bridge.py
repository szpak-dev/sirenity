import re

from jsonschema import Draft202012Validator, ValidationError

from sirenity.contexts.runtime.adapter import SirenAdapter, SirenAdapterRequest
from sirenity.contexts.shared import BaseState, SirenContractError, SirenityError

from ..values import SirenMcpInvocation, SirenMcpOperation, SirenMcpResult, SirenMcpTool


class SirenMcpBridge(BaseState):
    adapter: SirenAdapter

    def tools(self) -> tuple[SirenMcpTool, ...]:
        values = []
        for operation in self.adapter.engine.api.operations:
            input = self.adapter.engine.operation_input(operation.name)
            properties = {}
            required = []
            for name in re.findall(r"\{([^}]+)\}", operation.route.path):
                properties[name] = {"type": "string"}
                required.append(name)
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
            for field in operation.fields:
                schema = body_properties.get(field.name)
                if not isinstance(schema, dict):
                    schema = {"type": "number" if field.type in {"number", "range"} else "string"}
                    if field.values:
                        schema["enum"] = list(field.values)
                properties[field.name] = schema
                if field.name in body_required:
                    required.append(field.name)
            if input is not None:
                for delegated in input.delegated_inputs:
                    properties[delegated.name] = delegated.definition
                    if delegated.required:
                        required.append(delegated.name)
            schema = {"type": "object", "properties": properties}
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
        path_names = tuple(re.findall(r"\{([^}]+)\}", operation.route.path))
        path_values = {name: arguments[name] for name in path_names if name in arguments}
        input = self.adapter.engine.operation_input(operation.name)
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
        query_names = {
            field.name for field in operation.fields if field.name not in body_names}
        query_values = {name: arguments[name] for name in query_names if name in arguments}
        body_values = {name: arguments[name] for name in body_names if name in arguments}
        header_values = {}
        cookie_values = {}
        if input is not None:
            for delegated in input.delegated_inputs:
                if delegated.name not in arguments:
                    continue
                if delegated.location == "body":
                    if delegated.name == "body":
                        body_values = {"body": arguments[delegated.name]}
                    else:
                        body_values[delegated.name] = arguments[delegated.name]
                elif delegated.location == "query":
                    query_values[delegated.name] = arguments[delegated.name]
                elif delegated.location == "header":
                    header_values[delegated.name] = arguments[delegated.name]
                else:
                    cookie_values[delegated.name] = arguments[delegated.name]
        allowed = set(path_names) | body_names | query_names | set(header_values) | set(cookie_values)
        if input is not None:
            allowed.update(item.name for item in input.delegated_inputs)
        unknown = sorted(set(arguments) - allowed)
        if unknown:
            raise SirenityError(
                f"Siren MCP invocation has unknown arguments for {operation.name}: {unknown}")
        required = set(path_names) | set(body_required)
        if input is not None:
            required.update(item.name for item in input.delegated_inputs if item.required)
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

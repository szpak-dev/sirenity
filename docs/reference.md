# Public API reference

The supported root imports below are generated from `sirenity.__all__`.

| Symbol | Purpose | Primary API |
| --- | --- | --- |
| `SirenAction` | Describe an available Siren action. | — |
| `SirenAdapter` | Project already-executed framework results through a startup-compiled Siren engine. | `match(method: <class 'str'>, path: <class 'str'>) -> sirenity.contexts.runtime.adapter.values.match.SirenAdapterMatch | None`<br>`dispatch_path(method: <class 'str'>, path: <class 'str'>) -> str | None`<br>`render_path(template: <class 'str'>, values: collections.abc.Mapping[str, JsonValue]) -> <class 'str'>`<br>`respond(request: <class 'sirenity.contexts.runtime.adapter.values.request.SirenAdapterRequest'>) -> <class 'sirenity.contexts.runtime.adapter.values.response.SirenAdapterResponse'>`<br>`capabilities(operation_id: <class 'str'>) -> frozenset[str]`<br>`error(request: <class 'sirenity.contexts.runtime.adapter.values.request.SirenAdapterRequest'>) -> <class 'sirenity.contexts.runtime.document.values.document.SirenDocument'>` |
| `SirenAdapterMatch` | !!! abstract "Usage Documentation" | — |
| `SirenAdapterPolicy` | Declare application-owned authorization and optional projection overrides. | — |
| `SirenAdapterProfile` | Extend a fresh adapter document using public normalized operation metadata. | `apply(operation_id: <class 'str'>, operation_input: sirenity.contexts.graph.model.values.input.SirenInput | None, operation_inputs: collections.abc.Mapping[str, sirenity.contexts.graph.model.values.input.SirenInput | None], document: collections.abc.Mapping[str, JsonValue], context: <class 'sirenity.contexts.runtime.request.values.response.SirenResponseContext'>) -> collections.abc.Mapping[str, JsonValue]` |
| `SirenAdapterRequest` | Describe one already-executed HTTP operation for Siren projection. | — |
| `SirenAdapterResponse` | Represent an HTTP-ready official Siren response without framework dependencies. | — |
| `SirenAllowAllPolicy` | Permit every capability owned by the matched operation's compiled graph scope. | `select(operation_id: str | None, status: <class 'int'>, request: <class 'object'>, result: JsonValue) -> <class 'sirenity.contexts.runtime.adapter.values.policy.SirenAdapterPolicy'>` |
| `SirenCapabilityPolicy` | Select application authorization and optional projection overrides for one response. | `select(operation_id: str | None, status: <class 'int'>, request: <class 'object'>, result: JsonValue) -> <class 'sirenity.contexts.runtime.adapter.values.policy.SirenAdapterPolicy'>` |
| `SirenCompatibilityFinding` | Describe one OpenAPI construct outside the current official-Siren boundary. | — |
| `SirenCompatibilityReport` | Expose deterministic OpenAPI-to-Siren compatibility findings. | `compatible: <class 'bool'>`<br>`render() -> <class 'str'>` |
| `SirenConfiguration` | Retain one resolved Siren adapter and policy for an application lifecycle. | `adapter() -> <class 'sirenity.contexts.runtime.adapter.state.adapter.SirenAdapter'>`<br>`django(get_response: collections.abc.Callable[[object], object]) -> <class 'sirenity.contexts.runtime.adapter.state.django.SirenDjangoMiddleware'>` |
| `SirenContext` | Supply runtime state used to project a Siren document. | — |
| `SirenContractError` | Indicate a Sirenity operation failure. | `location: <class 'str'>`<br>`category: <class 'str'>`<br>`detail: <class 'str'>` |
| `SirenDelegatedInput` | !!! abstract "Usage Documentation" | — |
| `SirenDjangoMiddleware` | Render negotiated Django Ninja/Ninja Extra JSON responses as Siren. | — |
| `SirenDocument` | Represent an official Siren entity document. | — |
| `SirenEmbeddedLink` | Represent a Siren sub-entity linked by URI. | — |
| `SirenEmbeddedRepresentation` | Represent a Siren sub-entity embedded in full. | — |
| `SirenField` | Describe an official Siren action field. | — |
| `SirenFieldValue` | Describe a selectable Siren action field value. | — |
| `SirenInput` | !!! abstract "Usage Documentation" | — |
| `SirenLink` | Describe a navigational Siren link. | — |
| `SirenMcpExecution` | Carry one caller-executed MCP operation result back to the bridge. | — |
| `SirenMcpExecutor` | Execute one normalized MCP operation exactly once. | `execute(operation: <class 'sirenity.contexts.runtime.mcp.values.operation.SirenMcpOperation'>) -> <class 'sirenity.contexts.runtime.mcp.values.execution.SirenMcpExecution'>` |
| `SirenMcpInvocation` | Describe arguments supplied to one compiled MCP operation tool. | — |
| `SirenMcpOperation` | Represent compiled MCP arguments separated by their HTTP placement. | — |
| `SirenMcpResult` | !!! abstract "Usage Documentation" | — |
| `SirenMcpTool` | !!! abstract "Usage Documentation" | — |
| `SirenMiddleware` | Install Siren through Django's standard middleware loader. | — |
| `SirenParameterInput` | !!! abstract "Usage Documentation" | — |
| `SirenRelationship` | Describe a runtime relationship to another OpenAPI resource. | — |
| `SirenResponseContext` | Supply an executed OpenAPI operation and result for operation-aware projection. | — |
| `SirenScope` | Enum where members are also (and must be) strings | — |
| `SirenStructuredFormProfile` | Emit the versioned structured-form extension for delegated inputs. | `apply(operation_id: <class 'str'>, operation_input: sirenity.contexts.graph.model.values.input.SirenInput | None, operation_inputs: collections.abc.Mapping[str, sirenity.contexts.graph.model.values.input.SirenInput | None], document: collections.abc.Mapping[str, JsonValue], context: <class 'sirenity.contexts.runtime.request.values.response.SirenResponseContext'>) -> collections.abc.Mapping[str, JsonValue]`<br>`enrich(entity: collections.abc.Mapping[str, JsonValue], operation_inputs: collections.abc.Mapping[str, sirenity.contexts.graph.model.values.input.SirenInput | None]) -> collections.abc.Mapping[str, JsonValue]`<br>`control(delegated: <class 'sirenity.contexts.graph.model.values.delegated_input.SirenDelegatedInput'>) -> collections.abc.Mapping[str, JsonValue]` |
| `SirenityError` | Indicate a Sirenity operation failure. | — |
| `audit` | Inspect a valid OpenAPI document against the current official-Siren support boundary. | — |
| `siren` | Compile a complete OpenAPI 3.1 document into a reusable Siren engine. | — |
| `siren_adapter` | Compile a framework-neutral boundary for operation-aware Siren HTTP responses. | — |
| `siren_configuration` | Resolve one immutable, shared Siren integration configuration. | — |
| `siren_mcp` | Expose every compiled OpenAPI operation as a correctly described MCP tool. | — |

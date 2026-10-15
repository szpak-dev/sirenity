# Architecture

Sirenity sits between an API contract and the transports that expose it. It does not become the application, and it
does not ask every adapter to reinterpret OpenAPI for itself.

## Public boundary

The supported surface is published through `sirenity.api` and intentionally re-exported from the package root for
consumer imports. Private compiler and runtime modules remain implementation details.

Applications supply four things: an OpenAPI document, application data, a capability decision, and—when an operation
must run—a caller-owned executor. Sirenity returns compiled engines, Siren documents, adapter responses, or typed MCP
results. Authentication, authorization rules, persistence, retries, and server lifecycle remain outside the package.

## Compilation

The compiler validates and normalizes the complete OpenAPI document into an immutable operation graph. Route
ownership, resource relationships, request inputs, response schemas, and OpenAPI links are resolved here.

Compilation is strict because later layers trust the graph. An ambiguous route, unsupported input, incomplete link,
or invalid schema fails during startup rather than being reinterpreted by an adapter during a request.

## Runtime projection

The runtime combines a compiled operation graph with one application result and its capabilities. It produces
official Siren links, actions, embedded representations, and properties without mutating either the graph or the
caller-owned value.

Optional profiles may add explicitly versioned representation metadata. They operate on fresh serialized documents
and do not change the compiled graph.

## Integration adapters

The framework-neutral adapter matches source and public routes, then projects an operation result that the
application has already executed. Django middleware adds content negotiation and request-path rewriting around the
same adapter boundary. The MCP bridge exposes the same operations as tools and turns executor results into typed
navigation.

Every integration therefore shares one compilation result. There is no second parser or alternate composition path.

## Dependency direction

Public API functions resolve configured services through the existing Wireup composition. Compiler contexts build
the immutable graph; runtime contexts consume it; adapters translate at the outer boundary. Shared vocabulary and
official-Siren schema support both sides without owning application policy.

The useful rule is simple: dependencies point toward typed contracts and compiled values, while framework and
transport details stay at the edge.

# Sirenity

**Your application decides what's allowed. Sirenity shows what comes next.**

OpenAPI describes the operations an API supports. Sirenity compiles that contract into one action graph and combines
it with application-owned capabilities at runtime. The result can be exposed as navigable
[Siren](https://github.com/kevinswiber/siren) responses or as typed MCP operations and navigation values.

Sirenity never decides what a caller may do and never replaces application execution. It makes the application's
decision concrete: links and actions for hypermedia clients, and bound invocations for agents.

Start with [Compile an OpenAPI document into Siren](tutorials/openapi-to-siren.md). It builds a small API contract,
projects one application result, and shows where capability policy changes the response.

Then [Expose typed MCP navigation](tutorials/typed-mcp-navigation.md) to compile the same kind of contract into MCP
tools, execute one caller-owned operation, and follow a response-bound invocation without parsing a URL.

Use the [how-to guides](how-to/index.md) when you already know the outcome you need. Read the
[explanations](explanation/index.md) when the boundary between OpenAPI, Siren, the application, and MCP is the
question. The [architecture](explanation/architecture.md) describes ownership and dependency direction, while the
[glossary](reference/glossary.md) fixes the vocabulary used throughout the project.

The [technical reference](reference/index.md) contains the compatibility boundary and generated public API.

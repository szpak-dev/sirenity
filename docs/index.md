# Sirenity

[Siren](https://github.com/kevinswiber/siren) is a hypermedia type for describing a resource together with its links,
embedded entities, and available actions. Sirenity compiles an OpenAPI document into the runtime graph needed to
produce those representations. Successful results can also advertise safe operations available afterward without
recommending which operation a client should choose.

Start with [Compile an OpenAPI document into Siren](tutorials/openapi-to-siren.md). It builds a small API contract,
projects one application result, and shows where capability policy changes the response.

Use the [how-to guides](how-to/index.md) when you already know the outcome you need. Read the
[explanations](explanation/index.md) when the boundary between OpenAPI, Siren, the application, and MCP is the
question. The [architecture](explanation/architecture.md) describes ownership and dependency direction, while the
[glossary](reference/glossary.md) fixes the vocabulary used throughout the project.

The [technical reference](reference/index.md) contains the compatibility boundary and generated public API.

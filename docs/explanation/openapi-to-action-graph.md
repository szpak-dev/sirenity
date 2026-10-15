# From OpenAPI to an executable action graph

OpenAPI is usually treated as a description handed to generators. Sirenity treats it as a contract that can be
compiled once and reused while the application is running.

Compilation resolves route ownership, operation identifiers, parameters, request bodies, response schemas, and
OpenAPI links into one typed graph. That graph supplies the facts needed by every integration: which operation owns
a path, which inputs it accepts, which relationships it advertises, and which public URL represents it.

The graph is deliberately policy-free. A capability set supplied for one application result selects operations from
the graph; it does not teach Sirenity how the application reached that decision. Authentication, authorization, and
business rules therefore stay in the application that already owns them.

This separation also explains the startup failure model. An unknown target operation or ambiguous input is a broken
contract, not a request-time surprise. Sirenity rejects it while compiling the graph. Once compilation succeeds,
adapters and MCP projection can trust the normalized operations instead of parsing OpenAPI again.

The practical consequence is small but important: one compiled graph can drive a direct Siren engine, framework
adapters, and MCP tools without creating three slightly different interpretations of the same API.
